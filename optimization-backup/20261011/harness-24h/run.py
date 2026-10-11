from pathlib import Path
import argparse, hashlib, json, os, re, statistics, subprocess, time

root = Path(__file__).parent
source = root / 'source'
parser = argparse.ArgumentParser()
parser.add_argument('kind', choices=['capture', 'proof', 'time', 'full', 'encoder', 'inference'])
parser.add_argument('label')
parser.add_argument('--workload',choices=['score','depth'],default='score')
parser.add_argument('--lanes', type=int, choices=[1, 2, 4], default=4)
parser.add_argument('--trials', type=int, default=10)
parser.add_argument('--epochs', type=int, default=96)
parser.add_argument('--start', type=int, default=64)
parser.add_argument('--update', action='store_true')
parser.add_argument('--buffers', type=int, choices=[4,8,16], default=4)
parser.add_argument('--variant',choices=['baseline','balanced','cache','batched','balanced_cache','balanced_order','batched_small','batch_16x32','batch_64x16','batch_64x64','batch_16x48'],default='baseline')
parser.add_argument('--profile-matrices',action='store_true')
parser.add_argument('--binary', default=str(root/'binaries/baseline'))
parser.add_argument('--profile', choices=['node','graph'])
parser.add_argument('--end', type=int)
parser.add_argument('--env', action='append', default=[])

args = parser.parse_args()
directory = root / 'runs' / args.label
directory.mkdir(parents=True, exist_ok=False)
previous = Path('/puffertank/experiments/nethack-compact-state-20261008/runs/followthrough_score_candidate_a/command.json')
if args.workload=='depth':
    assert args.kind=='full', 'The saved GPU batch is the score workload.'
    previous=previous.parent.parent/'followthrough_depth_candidate_a/command.json'
manifest = json.loads(previous.read_text())
command = manifest['command']
command[0] = args.binary
for i, arg in enumerate(command):
    if arg.startswith('--base.checkpoint_dir='): command[i] = '--base.checkpoint_dir=' + str(directory / 'checkpoints')
    if arg.startswith('--base.log_dir='): command[i] = '--base.log_dir=' + str(directory / 'logs')
    if arg.startswith('--train.total_timesteps='): command[i] = '--train.total_timesteps=' + str(args.epochs * 262144)
    if arg.startswith('--vec.num_buffers='): command[i] = '--vec.num_buffers=' + str(args.buffers)
if args.buffers != 4:
    assert args.kind == 'full' and args.workload == 'score' and not args.update
environment = {k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','GOMP_','PUF_','PUFFER_','BENCH_','CUDA_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA','CUBLAS_WORKSPACE_CONFIG')}
environment.update(manifest['environment_overrides'])
environment.update(PUF_PERF_LOADED_PROOF=str(directory/'loaded.bin'), NH_GRAD_PIPELINE='3', CUDA_DEVICE_MAX_CONNECTIONS='32', PUF_MUON_LANES=str(args.lanes), BENCH_CAPTURE_START=str(args.start), BENCH_CAPTURE_END=str(args.epochs-1))
if args.variant in ['balanced','balanced_cache','balanced_order']:
    environment['PUF_MUON_COST_FILE']=str(root/'matrix_costs.txt')
if args.variant in ['cache','balanced_cache']: environment['PUF_CACHE_TABLES']='1'
if args.variant=='batched': environment['PUF_MUON_BATCHED']='1'
if args.variant=='balanced_order': environment['PUF_MUON_KEEP_ORDER']='1'
if args.variant=='batched_small': environment.update(PUF_MUON_BATCHED='1',PUF_MUON_BATCH_LIMIT='4096')
if args.variant.startswith('batch_'):
    environment.update(PUF_MUON_BATCHED='1',PUF_MUON_BATCH_SHAPE=args.variant.removeprefix('batch_'))
if args.profile_matrices: environment['PUF_MUON_PROFILE']='1'
if args.end is not None: environment['BENCH_CAPTURE_END']=str(args.end)
for assignment in args.env:
    key, value = assignment.split('=',1)
    assert key.startswith(('NH_', 'PUF_', 'CUDA_')) or key == 'LD_LIBRARY_PATH', key
    environment[key] = value

# Live-action validation cannot use the replay-only duplicate-copy assertion.
# Removing the replay input also makes the mode unambiguously live at startup.
if environment.get('PUF_LIVE_AFTER_WARM'):
    environment.pop('PUF_ACTION_REPLAY', None)

if args.kind in ['encoder','inference']:
    environment.update(NH_ENCODER_BENCH='1',NH_ENCODER_OUTPUT=str(directory/'encoder.bin'))
    if args.kind=='inference':environment['NH_INFERENCE_BENCH']='1'
if args.kind == 'capture':
    assert not (root/'mature_batch.bin').exists()
    environment.update(NH_PIPELINE_DUMP=str(root/'mature_batch.bin'), NH_PIPELINE_DUMP_EPOCH='64')
elif args.kind in ['proof', 'time', 'encoder', 'inference']:
    environment.update(NH_PIPELINE_LOAD=str(root/'mature_batch.bin'), NH_PIPELINE_TRIALS=str(args.trials))
    if args.kind == 'proof':
        (directory/'state').mkdir()
        environment['NH_PIPELINE_PROOF'] = str(directory/'state')
        environment.pop('PUF_PERF_FREEZE', None)
if args.update:
    environment.pop('PUF_PERF_FREEZE', None)
    (directory/'state').mkdir()
    environment['PUF_STATE_PROOF'] = str(directory/'state')
sha = lambda p: hashlib.file_digest(open(p,'rb'), 'sha256').hexdigest()
manifest.update(command=command, environment_overrides={k:v for k,v in environment.items() if k.startswith(('NH_','PUF_','BENCH_','CUDA_','OMP_','NETHACK')) or k=='LD_LIBRARY_PATH'}, binary_sha256=sha(command[0]), kind=args.kind, workload=args.workload, lanes=args.lanes, variant=args.variant, buffers=args.buffers, configuration_experiment=args.buffers!=4)
if args.profile:
    environment['PUF_SIZE_CAPTURE']='1'
    command=['nsys','profile','--trace=cuda,nvtx,osrt','--osrt-threshold=10000',
        '--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi',
        '--capture-range-end=stop','--cuda-graph-trace='+args.profile,
        '--wait=all','--kill=none','--output='+str(directory/'timeline'),*command]
    manifest['environment_overrides']['PUF_SIZE_CAPTURE']='1'
    manifest['command']=command
manifest['profile']=args.profile
(directory/'command.json').write_text(json.dumps(manifest, indent=2))
apps = subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True).strip()
assert not apps, apps
started=time.time()
with (directory/'gpu.csv').open('w') as gpu, (directory/'run.log').open('w') as log:
    monitor=subprocess.Popen(['nvidia-smi','--query-gpu=timestamp,utilization.gpu,power.draw,clocks.sm,temperature.gpu,memory.used','--format=csv,noheader,nounits','--loop-ms=1000'],stdout=gpu,stderr=subprocess.DEVNULL)
    try:
        process=subprocess.Popen(command,cwd=source,env=environment,stdout=log,stderr=subprocess.STDOUT)
        (root/'ACTIVE.json').write_text(json.dumps({'pid':process.pid,'label':args.label,'kind':args.kind,'started':started}))
        print('START',args.label,'pid',process.pid,flush=True)
        rc=process.wait()
    finally:
        monitor.terminate(); monitor.wait()
if rc == 0 and args.profile:
    with (directory/'export.log').open('w') as export:
        subprocess.run(['nsys','export','--type=sqlite','--output='+str(directory/'timeline.sqlite'),str(directory/'timeline.nsys-rep')],stdout=export,stderr=subprocess.STDOUT,check=True)
log=(directory/'run.log').read_text(errors='replace')
result={'profile':args.profile,'label':args.label,'kind':args.kind,'workload':args.workload,'lanes':args.lanes,'variant':args.variant,'buffers':args.buffers,'configuration_experiment':args.buffers!=4,'rc':rc,'wall_seconds':time.time()-started}
if rc == 0:
    if args.kind == 'capture':
        assert 'PIPELINE_SAVED' in log
        result['capture']=re.findall(r'PIPELINE_SAVED[^\n]+',log)
        result['capture_bytes']=(root/'mature_batch.bin').stat().st_size
        result['capture_sha256']=sha(root/'mature_batch.bin')
    elif args.kind in ['proof','time','encoder','inference']:
        assert 'PIPELINE_COMPLETE' in log
        rows=[{'trial':int(t),'milliseconds':float(ms),'model_ms':float(md)} for t,ms,md in re.findall(r'PIPELINE_TRIAL trial=(-?\d+) milliseconds=([\d.]+) model_ms=([\d.]+)',log)]
        result['trials']=rows
        result['mean_ms']=statistics.mean(x['milliseconds'] for x in rows if x['trial']>=0)
        if args.kind=='proof': result['state_hashes']={p.name:sha(p) for p in (directory/'state').glob('*.bin')}
    else:
        def rows(tag): return [{k:float(v) for k,v in re.findall(r'(\w+)=([\d.]+)',ln)} for ln in log.splitlines() if ln.startswith(tag)]
        result.update(epochs=rows('BATCH_PERF'), clocks=rows('BENCH_CLOCK'), ages=rows('PERF_EPOCH'),proofs=re.findall(r'BATCH_PROOF epoch=(\d+) obs=([0-9a-f]+) params=(\d+) copies=(\d+)',log))
        clocks={int(x['epoch']):x['time'] for x in result['clocks']}
        result['sps']=(args.epochs-1-args.start)*262144/(clocks[args.epochs-2]-clocks[args.start-1])
        result['initial_sha']=sha(directory/'loaded.bin')
        result['final_sha']=sha(directory/'checkpoints/nethack/profile'/f'{args.epochs*262144:016d}.bin')
        if not args.update: assert result['initial_sha']==result['final_sha']
        if args.update: result['rollout_hashes'] = (directory/'state/rollout.hashes').read_text()
        if args.update: result['state_hashes']={p.name:sha(p) for p in (directory/'state').glob('*.bin')}
else:
    result['failure']=log[-5000:]
(directory/'result.json').write_text(json.dumps(result,indent=2))
(root/'ACTIVE.json').write_text(json.dumps({'status':'idle','last':args.label,'rc':rc}))
print('DONE',json.dumps({k:v for k,v in result.items() if k not in ('trials','epochs','clocks','ages','proofs')}),flush=True)
raise SystemExit(rc)
