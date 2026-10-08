from pathlib import Path
import os,subprocess,json,hashlib,time,re
r=Path(__file__).resolve().parent;old=Path('/puffertank/experiments/nethack-perf-20260917');out=r/'training';out.mkdir();rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
e={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA')};e.update(NETHACKDIR=str(old/'dat'),NH_ZT_MASK='0',CUDA_VISIBLE_DEVICES='0',LD_LIBRARY_PATH=str(old/'variants/candidate14-lto-local'))
for w,tree in [('depth','depth-source'),('score','source')]:
 ckpt=Path('/puffertank/experiments/depth4b-20260916/checkpoints/nethack/depth4b_s901/0000003999989760.bin') if w=='depth' else Path('/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin');args=json.loads(Path('/puffertank/experiments/depth4b-20260916/manifest.json').read_text())['args'] if w=='depth' else ['--base.env_name=nethack'];steps=4194304 if w=='depth' else 16777216
 for phase,bin in [('before','puffer_baseline'),('heads','puffer_heads'),('after','puffer_baseline')]:
  label=w+'-'+phase;d=out/label;d.mkdir();cmd=[str(r/tree/bin),'train','--headless',*args,'--train.total_timesteps='+str(steps),'--base.seed=901','--base.run_id=sampler','--base.eval_episodes=8','--base.eval_agents=8','--base.checkpoint_dir='+str(d/'checkpoints'),'--base.log_dir='+str(d/'logs')];t=time.time();print('START',label,flush=True)
  with (d/'log').open('w') as f:p=subprocess.run(cmd,cwd=r/tree,env=dict(e,NH_DISC_SWAP='1' if w=='depth' else '0',OMP_NUM_THREADS='24' if w=='depth' else '32',PUF_PERF_START_WEIGHTS=str(ckpt),PUF_PERF_LOADED_PROOF=str(d/'loaded.bin')),stdout=f,stderr=subprocess.STDOUT)
  s=(d/'log').read_text(errors='replace');epochs=[dict(re.findall(r'(\w+)=([^ ]+)',x)) for x in s.splitlines() if x.startswith('PERF_EPOCH ')];row=dict(label=label,rc=p.returncode,command=cmd,seconds=time.time()-t,epochs=epochs,binary_sha=sha(r/tree/bin));rows.append(row);(out/'results.json').write_text(json.dumps(rows,indent=2));assert p.returncode==0 and len(epochs)==64
  assert sha(d/'loaded.bin')==sha(ckpt);assert any(int(p.stem)>=steps for p in (d/'checkpoints/nethack/sampler').glob('*.bin'));assert not re.search(r'(?i)(?:^|\s)(?:nan|[+-]?inf)(?:\s|$)',s)
  row.update(weights_sha=sha(ckpt),later_seconds=sum(float(x['seconds']) for x in epochs[32:]),later_steps=steps//2,mean_turn=sum(float(x['mean_turn']) for x in epochs[32:])/32);(out/'results.json').write_text(json.dumps(rows,indent=2));print('DONE',label,row['later_seconds'],flush=True)
print('DONE',flush=True)
