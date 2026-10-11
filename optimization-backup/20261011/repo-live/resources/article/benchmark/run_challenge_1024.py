"""Extend the unchanged three-backend challenge benchmark to 1024 games."""
import json,time,hashlib
from run_challenge import trial
from run import B,CASES,ENGINES
meta=json.loads((B/'challenge_machine.json').read_text())
for name,digest in {**meta['source_hashes'],**meta['binary_hashes']}.items():
 assert hashlib.sha256((B/name).read_bytes()).hexdigest()==digest,name
original=json.loads((B/'machine.json').read_text())
for v in original['binaries'].values():
 assert hashlib.sha256(open(v['path'],'rb').read()).hexdigest()==v['sha256']
rows=[]
with (B/'challenge_1024_timings.jsonl').open('w') as f:
 for case in CASES:
  for rep in range(4):
   order=['stock','python','fast'];offset=rep%3;order=order[offset:]+order[:offset];group=[]
   for kind in order:
    d=trial(kind,1024,case,rep);rows.append(d);group.append(d);f.write(json.dumps(d)+'\n');f.flush()
   assert len({d['final_hash'] for d in group})==1 and len({d['turn_advances'] for d in group})==1
(B/'challenge_1024_complete.json').write_text(json.dumps(dict(trials=len(rows),all_triples_match=True,completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())),indent=2))
