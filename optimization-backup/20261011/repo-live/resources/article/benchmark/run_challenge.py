"""Compare stock C, actual gym.step, and fast C with matched observations."""
import subprocess,os,time,json,hashlib
from run import B,ROOT,CASES,ENGINES

def trial(kind,total,case,rep):
 name,steps=case;workers=8
 env=dict(os.environ,LD_PRELOAD=str(B/'faketime.so'),NLE_FAKE_TIME='1600000000',TZ='UTC',BENCH_BARRIER='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
 ps=[];pss=0
 for w in range(1 if kind=='fast' else workers):
  e=dict(env,BENCH_THREADS=str(8 if kind=='fast' else 1))
  if kind!='fast':e['BENCH_CPU']=str(w*2)
  if kind=='python':cmd=['/puffertank/venv/bin/python',str(B/'challenge_worker.py'),str(B/'workloads'/name),str(total//workers),str(steps),'-']
  else:cmd=[str(B/f'challenge_{kind}_c'),*ENGINES[kind],str(B/'workloads'/name),str(total if kind=='fast' else total//workers),str(steps),'1','-']
  ps.append(subprocess.Popen(cmd,env=e,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True))
 for p in ps:
  line=p.stdout.readline()
  if line.strip()!='READY':raise RuntimeError((line,p.stderr.read()))
  for l in open(f'/proc/{p.pid}/smaps_rollup'):
   if l.startswith('Pss:'):pss+=int(l.split()[1])
 for p in ps:p.stdin.write('\n');p.stdin.flush()
 values=[]
 for p in ps:
  line=p.stdout.readline()
  try: values.append(json.loads(line))
  except Exception:raise RuntimeError((line,p.stderr.read()))
 for p in ps:
  p.stdin.close();p.wait(timeout=60)
  if p.returncode:raise RuntimeError(p.stderr.read())
 assert len({v['final_hash'] for v in values})==1
 calls=sum(v['calls'] for v in values);seconds=max(v['seconds'] for v in values)
 d=dict(engine=kind,workers=workers,envs=total,case=name,rep=rep,calls=calls,seconds=seconds,sps=calls/seconds,pss_kib=pss,final_hash=values[0]['final_hash'],turn_advances=sum(v['turn_advances'] for v in values),final_turn=values[0]['final_turn'],final_score=values[0]['final_score'])
 print(json.dumps(d),flush=True);return d

if __name__=='__main__':
 assert len(json.loads((B/'challenge_validation.json').read_text()))==3
 meta={'python':'/puffertank/venv/bin/python','gym':'0.23.0','nle':'0.9.0','source_hashes':{n:hashlib.sha256((B/n).read_bytes()).hexdigest() for n in ['challenge_worker.py','engine_challenge.c','run_challenge.py']},'binary_hashes':{n:hashlib.sha256((B/n).read_bytes()).hexdigest() for n in ['challenge_stock_c','challenge_fast_c','faketime.so']},'start_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 (B/'challenge_machine.json').write_text(json.dumps(meta,indent=2))
 rows=[]
 with (B/'challenge_timings.jsonl').open('w') as f:
  for total in (8,128,512):
   for case in CASES:
    for rep in range(4):
     order=['stock','python','fast'];offset=rep%3;order=order[offset:]+order[:offset];group=[]
     for kind in order:
      d=trial(kind,total,case,rep);rows.append(d);group.append(d);f.write(json.dumps(d)+'\n');f.flush()
     assert len({d['final_hash'] for d in group})==1 and len({d['turn_advances'] for d in group})==1
 (B/'challenge_complete.json').write_text(json.dumps(dict(trials=len(rows),all_triples_match=True),indent=2))
