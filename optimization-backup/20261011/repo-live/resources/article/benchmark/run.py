import subprocess,os,json,time,hashlib,statistics as st,platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; B=Path(__file__).resolve().parent
ENGINES={'stock':('/puffertank/nle-stock/nle/libnethack.so','/puffertank/nle-stock/nle/nethackdir'),'fast':(str(ROOT/'vendor/fast-nle/build/libnethack.so'),str(ROOT/'vendor/fast-nle/build/dat'))}
CASES=[('pri_seed1012_2025.golden',1500),('rog_seed1016_2033.golden',968),('sam_seed1018_2037.golden',358)]
def trial(kind,workers,total,case,tty,rep):
 lib,dat=ENGINES[kind];name,steps=case
 env=dict(os.environ,LD_PRELOAD=str(B/'faketime.so'),NLE_FAKE_TIME='1600000000',TZ='UTC',BENCH_BARRIER='1')
 ps=[];pss=0
 for w in range(workers if kind=='stock' else 1):
  e=dict(env,BENCH_THREADS=str(workers if kind=='fast' else 1))
  if kind=='stock':e['BENCH_CPU']=str(w*2)
  cmd=[str(B/f'engine_{kind}'),lib,dat,str(ROOT/'vendor/fast-nle/tests/goldens'/name),str(total//workers if kind=='stock' else total),str(steps),str(tty),'-']
  p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=e);ps.append(p)
 for p in ps:
  line=p.stdout.readline()
  if line.strip()!='READY':raise RuntimeError((p.pid,line,p.stderr.read()))
  for l in Path(f'/proc/{p.pid}/smaps_rollup').read_text().splitlines():
   if l.startswith('Pss:'):pss+=int(l.split()[1])
 t=time.perf_counter()
 for p in ps:p.stdin.write('\n');p.stdin.flush()
 vals=[]
 for p in ps:
  # The first JSON line is emitted before cleanup, so cleanup is not timed.
  line=p.stdout.readline()
  try: vals.append(json.loads(line))
  except Exception:raise RuntimeError((line,p.stderr.read()))
 wall=time.perf_counter()-t
 for p in ps:
  p.stdin.close();p.wait(timeout=60)
  if p.returncode:raise RuntimeError((p.returncode,p.stderr.read()))
 assert len({x['final_hash'] for x in vals})==1
 calls=sum(v['calls'] for v in vals);duration=max(v['seconds'] for v in vals)
 out=dict(engine=kind,workers=workers,envs=total,case=name,keys=steps,tty=tty,rep=rep,calls=calls,seconds=duration,sps=calls/duration,wall_seconds=wall,pss_kib=pss,init_seconds=sum(v['init_seconds'] for v in vals),turn_advances=sum(v['turn_advances'] for v in vals),final_hash=vals[0]['final_hash'],final_turn=vals[0]['final_turn'],final_score=vals[0]['final_score'])
 print(json.dumps(out),flush=True)
 return out
if __name__=='__main__':
 meta=dict(time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),cpu=subprocess.check_output(['lscpu'],text=True),platform=platform.platform(),binaries={k:dict(path=v[0],sha256=hashlib.sha256(Path(v[0]).read_bytes()).hexdigest()) for k,v in ENGINES.items()},source_sha256=hashlib.sha256((B/'engine.c').read_bytes()).hexdigest())
 (B/'machine.json').write_text(json.dumps(meta,indent=2))
 rows=[]
 with (B/'timings.jsonl').open('w') as f:
  for tty,workers,total in [(0,1,1),(0,1,128),(0,4,128),(0,8,128),(1,1,128)]:
   for case in CASES:
    for rep in range(4):
     pair=[]
     for kind in (['stock','fast'] if rep%2==0 else ['fast','stock']):
      d=trial(kind,workers,total,case,tty,rep);pair.append(d);rows.append(d);f.write(json.dumps(d)+'\n');f.flush()
     assert pair[0]['final_hash']==pair[1]['final_hash'] and pair[0]['turn_advances']==pair[1]['turn_advances'],pair
 (B/'complete.json').write_text(json.dumps(dict(trials=len(rows),all_pairs_match=True),indent=2))
