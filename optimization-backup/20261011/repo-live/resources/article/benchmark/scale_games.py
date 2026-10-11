"""Fixed eight-core scaling with increasing concurrent environments."""
import json, time
from run import B, CASES, trial
rows=[]
with (B/'scaling_games.jsonl').open('w') as f:
 for total in (8,32,128,512,1024):
  for case in CASES:
   for rep in range(4):
    pair=[]
    for kind in (['stock','fast'] if rep%2==0 else ['fast','stock']):
     row=trial(kind,8,total,case,0,rep)
     rows.append(row);pair.append(row);f.write(json.dumps(row)+'\n');f.flush()
    assert pair[0]['final_hash']==pair[1]['final_hash'] and pair[0]['turn_advances']==pair[1]['turn_advances']
(B/'scaling_complete.json').write_text(json.dumps({'trials':len(rows),'all_pairs_match':True,'completed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},indent=2))
