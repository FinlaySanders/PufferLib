from pathlib import Path
import os,subprocess,json,hashlib,time,concurrent.futures,threading,collections
r=Path('/workspace/experiments/nethack-landmarks-20260914')
base=Path('/workspace/experiments/nethack-depth-2b-20260914')
lock=threading.Lock()
def event(kind,**kw):
 row=dict(event=kind,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**kw)
 with lock:
  with (r/'queue.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  print(json.dumps(row),flush=True)
def run(seed,gpu,name,instrumented=True,smoke=False):
 lib=r/'lib' if instrumented else base/'lib'
 e={k:v for k,v in os.environ.items() if not k.startswith('NH_') and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','NETHACKOPTIONS','NLE_STOCK_LIB')}
 ep=r/(name+'.ep');assert not ep.exists()
 e.update(CUDA_VISIBLE_DEVICES=str(gpu),LD_LIBRARY_PATH=str(lib),NETHACKDIR=str(r/'dat'),OMP_NUM_THREADS='1' if smoke else '24',NH_EPLOG=str(ep))
 ckpt=base/f'checkpoints/nethack/depth2b_s{seed}/0000001999962112.bin';assert ckpt.exists()
 cmd=[str((r if instrumented else base)/'puffer'),'eval','--headless',f'--base.load_model_path={ckpt}',f'--base.run_id={name}','--base.seed=7',f'--base.eval_episodes={128 if smoke else 14000}']
 if smoke:cmd+=['--base.eval_agents=16','--vec.num_buffers=1','--vec.num_threads=1']
 with (r/(name+'.log')).open('x') as f:
  p=subprocess.Popen(cmd,cwd=r,env=e,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
  event('START',name=name,gpu=gpu,pid=p.pid,command=cmd)
  rc=p.wait()
 event('EXIT',name=name,rc=rc)
 assert rc==0,name
 rows=[list(map(int,line.split())) for line in ep.read_text().splitlines() if line.strip()]
 assert all(len(x)==(15 if instrumented else 11) for x in rows)
 if instrumented:
  assert all(x[11] in (0,1) and x[12] in (0,1) and 21<=x[13]<=28 and 25<=x[14]<=29 for x in rows)
 return rows
assert (r/'BUILD_DONE').exists()
manifest=dict(source=str(base),cohort='depth-trained',steps='2B',interface='fork',seeds=list(range(801,809)),evaluation_seed=7,burnin_per_seed=4000,kept_per_seed=10000,columns=['score','how','time','noprog','role','race','gender','max_depth','last_turn','killer','killer_level','visited_medusa','visited_castle','medusa_depth','castle_depth'],sha256={})
for p in [r/'puffer',r/'lib/libnethack.so',r/'source.patch',r/'engine.patch',r/'config/nethack.ini',r/'config/default.ini']:
 manifest['sha256'][str(p.relative_to(r))]=hashlib.sha256(p.read_bytes()).hexdigest()
(r/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
a=run(801,0,'smoke_original',False,True);b=run(801,0,'smoke_instrumented',True,True)
assert a==[x[:11] for x in b], 'Instrumentation changed deterministic episode outcomes'
event('SMOKE_PARITY',episodes=len(a),medusa=sum(x[11] for x in b),castle=sum(x[12] for x in b))
def lane(gpu,seed):
 name=f'landmarks_s{seed}'
 rows=run(seed,gpu,name)[4000:14000];assert len(rows)==10000
 result=dict(seed=seed,n=len(rows),medusa=sum(x[11] for x in rows),castle=sum(x[12] for x in rows),roles=[dict(role=role,n=sum(x[4]==role for x in rows),medusa=sum(x[11] for x in rows if x[4]==role),castle=sum(x[12] for x in rows if x[4]==role)) for role in range(13)])
 (r/(name+'_results.json')).write_text(json.dumps(result,indent=2)+'\n')
 with (r/(name+'_analyze.txt')).open('w') as f:subprocess.run(['python3',str(base/'analyze.py'),str(r/(name+'.ep'))],stdout=f,check=True)
 event('EVAL_DONE',**result)
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 results=list(pool.map(lambda gs:lane(*gs),enumerate(range(801,809))))
(r/'results.json').write_text(json.dumps(dict(manifest=manifest,runs=results),indent=2)+'\n')
event('QUEUE_DONE')
