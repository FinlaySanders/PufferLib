import subprocess,os,json
from pathlib import Path
from run import B,ROOT,CASES,ENGINES
E=dict(os.environ,LD_PRELOAD=str(B/'faketime.so'),NLE_FAKE_TIME='1600000000',TZ='UTC')
out=[]
for name,limit in CASES:
 traces={}
 for kind in ('stock','fast','python'):
  path=B/f'{kind}_challenge.trace';case=str(B/'workloads'/name)
  if kind=='python':cmd=['/puffertank/venv/bin/python',str(B/'challenge_worker.py'),case,'1',str(limit),str(path)]
  else:cmd=[str(B/f'challenge_{kind}_c'),*ENGINES[kind],case,'1',str(limit),'1',str(path)]
  p=subprocess.run(cmd,env=E,capture_output=True,text=True,timeout=30)
  if p.returncode:raise RuntimeError((kind,p.stdout,p.stderr))
  traces[kind]=[l.split()[1] for l in path.read_text().splitlines()]
 assert len(traces['stock'])==limit
 assert traces['stock']==traces['fast']==traces['python'],name
 out.append(dict(case=name,keys=limit,all_14_public_channels_match_every_key=True));print(out[-1],flush=True)
(B/'challenge_validation.json').write_text(json.dumps(out,indent=2))
