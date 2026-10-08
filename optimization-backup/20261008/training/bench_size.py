from pathlib import Path
import os,subprocess,json,hashlib,time,re,statistics,sys
r=Path(__file__).parent;s=r/'source'
label,binary=sys.argv[1:3];update='--update' in sys.argv;profile=next((x.split('=')[1] for x in sys.argv if x.startswith('--profile=')),None)
d=r/label;d.mkdir();base={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','GOMP_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA')}
base.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0',NH_DISC_SWAP='0',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='32',PUF_POOL_WORKERS='24',LD_LIBRARY_PATH='/puffertank/experiments/nethack-overnight-20260917/pgo61/variant',PUF_BATCH_REPLAY='1',PUF_ACTION_REPLAY='/puffertank/experiments/nethack-size-profile-20260918/actions',PUF_PERF_START_WEIGHTS='/puffertank/pufferlib/resources/nethack/fixwt4b_s705.bin',PUF_PERF_LOADED_PROOF=str(d/'loaded.bin'))
base.update(dict(x[6:].split('=',1) for x in sys.argv if x.startswith('--env=')))
width=int(next((x.split('=')[1] for x in sys.argv if x.startswith('--width=')),'1024'))
if width!=1024:base.pop('PUF_PERF_START_WEIGHTS',None)
if not update:base['PUF_PERF_FREEZE']='1'
if profile:base['PUF_SIZE_CAPTURE']='1'
cmd=[binary,'train','--headless','--base.env_name=nethack','--train.total_timesteps=4194304',f'--policy.hidden_size={width}','--policy.num_layers=4','--vec.total_agents=512','--train.minibatch_size=4096','--vec.num_threads=32','--vec.num_buffers=4','--base.profile=1','--base.seed=901','--base.run_id=profile','--base.eval_episodes=0','--base.checkpoint_dir='+str(d/'checkpoints'),'--base.log_dir='+str(d/'logs')]
if profile:cmd=['nsys','profile','--trace=cuda,nvtx,osrt','--osrt-threshold=10000','--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi','--capture-range-end=stop','--cuda-graph-trace='+profile,'--wait=all','--kill=none','--output='+str(d/'timeline'),*cmd]
(d/'command.json').write_text(json.dumps({'command':cmd,'environment_overrides':{k:v for k,v in base.items() if k.startswith(('PUF_','NH_','NETHACK','CUDA_','OMP_')) or k=='LD_LIBRARY_PATH'}},indent=2))
print('START',label,flush=True);t=time.time()
with (d/'run.log').open('w') as f:rc=subprocess.call(cmd,cwd=s,env=base,stdout=f,stderr=subprocess.STDOUT)
out=dict(label=label,rc=rc,wall=time.time()-t,update=update,profile=profile)
if rc==0:
 log=(d/'run.log').read_text(errors='replace');proofs=re.findall(r'BATCH_PROOF epoch=(\d+) obs=([0-9a-f]+) params=(\d+) copies=(\d+)',log)
 assert [(a,b) for a,b,c,e in proofs]==[('7','682be6438987b7c7'),('13','1c94b03758f7db94'),('15','9621d2ab6f2f097e')],proofs
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();final=d/'checkpoints/nethack/profile/0000000004194304.bin'
 out.update(initial_sha=sha(d/'loaded.bin'),final_sha=sha(final),proofs=proofs)
 if not update:assert out['initial_sha']==out['final_sha']
 rows=[]
 for line in log.splitlines():
  if 'BATCH_PERF ' in line:rows.append({k:float(v) for k,v in re.findall(r'(\w+)=([\d.]+)',line)})
 timed=[v for v in rows if 8<=v['epoch']<=13];assert len(timed)==6
 mean=lambda k:statistics.mean(x[k] for x in timed)
 out.update(seconds=mean('seconds'),sps=262144/mean('seconds'),rollout_tail=mean('rollout_tail'),ppo_tail=mean('ppo_tail'),used_mib=max(x['used_mib'] for x in rows),epochs=timed)
 if profile:
  with (d/'export.log').open('w') as f:subprocess.run(['nsys','export','--type=sqlite','--output='+str(d/'timeline.sqlite'),str(d/'timeline.nsys-rep')],stdout=f,stderr=subprocess.STDOUT,check=True)
else:out['failure']=(d/'run.log').read_text(errors='replace')[-3000:]
(d/'result.json').write_text(json.dumps(out,indent=2));print('DONE',json.dumps({k:v for k,v in out.items() if k not in ('epochs','proofs')}),flush=True)
if rc:sys.exit(1)
