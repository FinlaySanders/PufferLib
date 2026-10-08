from pathlib import Path
import os,subprocess,json,hashlib,time
r=Path(__file__).resolve().parent;old=Path('/puffertank/experiments/nethack-perf-20260917');out=r/'native';out.mkdir();rows=[]
e={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','PUF_','PUFFER_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS','NVCC_EXTRA')};e.update(NETHACKDIR=str(old/'dat'),NH_ZT_MASK='0',OMP_NUM_THREADS='8',CUDA_VISIBLE_DEVICES='0',LD_LIBRARY_PATH=str(old/'variants/candidate14-lto-local'))
for w,tree in [('depth','depth-source'),('score','source')]:
 base=json.loads((old/('smoke-command.json' if w=='depth' else 'score-smoke-command.json')).read_text());base=[s for s in base if not s.startswith(('--vec.num_buffers=','--vec.num_threads=','--base.async=','--base.cudagraphs='))];base+=['--vec.num_buffers=4','--vec.num_threads=8','--base.async=1','--base.cudagraphs=-1'];proof=[]
 for name in ['puffer_baseline','puffer_heads']:
  d=out/(w+'-'+name);d.mkdir();tr=d/'traces';obs=d/'observations';tr.mkdir();obs.mkdir();cmd=list(base);cmd[0]=str(r/tree/name);t=time.time()
  with (d/'log').open('w') as f:p=subprocess.run(cmd,cwd=r/tree,env=dict(e,NH_DISC_SWAP='1' if w=='depth' else '0',NH_PERF_RECORD=str(tr),NH_PERF_SNAPSHOTS=str(obs)),stdout=f,stderr=subprocess.STDOUT)
  hashes={str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [tr,obs] for p in folder.iterdir()};assert hashes
  row=dict(workload=w,binary=name,rc=p.returncode,seconds=time.time()-t,command=cmd,hashes=hashes);rows.append(row);proof.append(hashes);(out/'results.json').write_text(json.dumps(rows,indent=2));print(w,name,p.returncode,flush=True);assert p.returncode==0
 assert proof[0]==proof[1],w+' trace/raw mismatch'
print('PASS both native trace and raw observation hashes',flush=True)
