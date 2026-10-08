from pathlib import Path
import os,subprocess,json,hashlib,time,re,statistics
r=Path(__file__).parent;s=r/'source'
base={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','GOMP_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA')}
base.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0',NH_DISC_SWAP='0',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='32',PUF_PERF_FREEZE='1',PUF_POOL_WORKERS='24',LD_LIBRARY_PATH='/puffertank/experiments/nethack-overnight-20260917/pgo61/variant',PUF_BATCH_REPLAY='1',PUF_ACTION_REPLAY='/puffertank/experiments/nethack-size-profile-20260918/actions')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
for n in (512,1024,2048,4096):
 for w in (224,512):
  for mb in (4096,16384,32768):
   label=f'h{w}-n{n}-mb{mb}';d=r/label;d.mkdir(exist_ok=True)
   if (d/'result.json').exists(): results.append(json.loads((d/'result.json').read_text()));continue
   steps=n*512*16;env=dict(base,PUF_PERF_LOADED_PROOF=str(d/'loaded.bin'))
   cmd=[str(s/'puffer_batch'),'train','--headless','--base.env_name=nethack',f'--train.total_timesteps={steps}',f'--policy.hidden_size={w}','--policy.num_layers=4',f'--vec.total_agents={n}',f'--train.minibatch_size={mb}','--vec.num_threads=32','--vec.num_buffers=4','--base.profile=1','--base.seed=901','--base.run_id=profile','--base.eval_episodes=0','--base.checkpoint_dir='+str(d/'checkpoints'),'--base.log_dir='+str(d/'logs')]
   (d/'command.json').write_text(json.dumps(dict(command=cmd,environment_overrides={k:env[k] for k in base if k.startswith(('PUF_','NH_','OMP_','CUDA_','NETHACK')) or k=='LD_LIBRARY_PATH'}),indent=2))
   print('START',label,flush=True);start=time.time()
   with (d/'run.log').open('w') as f: rc=subprocess.call(cmd,cwd=s,env=env,stdout=f,stderr=subprocess.STDOUT)
   out=dict(label=label,width=w,agents=n,minibatch=mb,rc=rc,wall_seconds=time.time()-start)
   if rc==0:
    log=(d/'run.log').read_text(errors='replace');proofs=re.findall(r'BATCH_PROOF epoch=(\d+) obs=([0-9a-f]+) params=(\d+) copies=(\d+)',log)
    expected=[('7','682be6438987b7c7'),('13','1c94b03758f7db94'),('15','9621d2ab6f2f097e')]
    assert [(a,b) for a,b,c,e in proofs]==expected,(label,proofs)
    final=d/f'checkpoints/nethack/profile/{steps:016d}.bin';assert sha(final)==sha(d/'loaded.bin'),label
    rows=[]
    for line in log.splitlines():
     if 'BATCH_PERF ' in line:
      vals=dict(re.findall(r'(\w+)=([\d.]+)',line));rows.append({k:float(v) for k,v in vals.items()})
    timed=[v for v in rows if 8<=v['epoch']<=13];assert len(timed)==6,(label,rows)
    mean=lambda k:statistics.mean(x[k] for x in timed)
    out.update(params=int(proofs[0][2]),sha256=sha(final),proofs=proofs,seconds=mean('seconds'),sps=n*512/mean('seconds'),rollout_tail=mean('rollout_tail'),ppo_tail=mean('ppo_tail'),used_mib=max(x['used_mib'] for x in rows),updates=timed[0]['updates'],epochs=timed)
   else: out['failure_tail']=(d/'run.log').read_text(errors='replace')[-3000:]
   (d/'result.json').write_text(json.dumps(out,indent=2));results.append(out);(r/'results.json').write_text(json.dumps(results,indent=2));print('DONE',label,json.dumps({k:v for k,v in out.items() if k not in ('epochs','proofs','failure_tail')}),flush=True)
print('SWEEP_DONE',flush=True)
