from pathlib import Path
import os,subprocess,json,hashlib,time,re,sys
r=Path(__file__).parent;s=r/'source';out=r/'training';out.mkdir(exist_ok=True)
phases=sys.argv[1:] or ['baseline-a','workspace','split','both','baseline-b']
e={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA')}
ckpt='/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin';e.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0',NH_DISC_SWAP='0',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='32',LD_LIBRARY_PATH='/puffertank/experiments/nethack-perf-20260917/variants/candidate14-lto-local',PUF_PERF_START_WEIGHTS=ckpt)
for label in phases:
 d=out/label;d.mkdir();binary='baseline' if label.startswith('baseline') else label
 cmd=[str(s/('puffer_'+binary)),'train','--headless','--base.env_name=nethack','--train.total_timesteps=8388608','--base.seed=901','--base.run_id=gemm','--base.eval_episodes=8','--base.eval_agents=8','--base.checkpoint_dir='+str(d/'checkpoints'),'--base.log_dir='+str(d/'logs')]
 print('START',label,flush=True);t=time.time()
 with (d/'log').open('w') as f:
  p=subprocess.run(cmd,cwd=s,env=dict(e,PUF_PERF_LOADED_PROOF=str(d/'loaded.bin')),stdout=f,stderr=subprocess.STDOUT)
 txt=(d/'log').read_text(errors='replace');epochs=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in re.findall(r'PERF_EPOCH [^\n]+',txt)]
 row=dict(label=label,rc=p.returncode,wall_seconds=time.time()-t,command=cmd,epochs=epochs)
 (d/'result.json').write_text(json.dumps(row,indent=2));assert p.returncode==0 and [int(x['epoch']) for x in epochs]==list(range(32)),label
 assert hashlib.sha256((d/'loaded.bin').read_bytes()).digest()==hashlib.sha256(Path(ckpt).read_bytes()).digest();assert (d/'checkpoints/nethack/gemm/0000000008388608.bin').exists()
 assert not re.search(r'(?i)(?:^|\s)(?:nan|[+-]?inf)(?:\s|$)',txt)
 # Last epoch omits prefetch; exclude it from comparisons.
 selected=epochs[16:31];row.update(timed_seconds=sum(float(x['seconds']) for x in selected),timed_steps=15*262144,mean_turn=sum(float(x['mean_turn']) for x in selected)/15)
 (d/'result.json').write_text(json.dumps(row,indent=2));print('DONE',label,'timed_seconds',row['timed_seconds'],'mean_turn',row['mean_turn'],flush=True)
