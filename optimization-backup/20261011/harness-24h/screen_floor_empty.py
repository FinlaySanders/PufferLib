from pathlib import Path
import json
import statistics
import sys

R=Path(__file__).resolve().parent
D=R/'floor_empty_study'
sys.path.insert(0,str(R/'native_pool'))
from snapshot_test import run

rows=[]
for role,engine in [('base_a','floor_empty_base'),('candidate_a','floor_empty_candidate'),('candidate_b','floor_empty_candidate'),('base_b','floor_empty_base')]:
    row=run('floor_empty_512_'+role,512,'0:2048,0:2048',engine=R/engine/'build',workers=32,pin=False)
    row['role']=role
    rows.append(row)
    (D/'SCREEN_512.json').write_text(json.dumps(rows,indent=2))
base=[float(c['result']['sps']) for row in rows if row['role'].startswith('base') for c in row['cases']]
candidate=[float(c['result']['sps']) for row in rows if row['role'].startswith('candidate') for c in row['cases']]
summary={'control_sps':statistics.mean(base),'candidate_sps':statistics.mean(candidate),'gain_percent':100*(statistics.mean(candidate)/statistics.mean(base)-1),'control_drift_percent':100*(statistics.mean(base[2:])/statistics.mean(base[:2])-1),'control_values':base,'candidate_values':candidate,'endpoints_ok':all(row['endpoints_ok'] for row in rows),'scope':'Matched ordinary LTO native replay at 512 envs/32 unpinned workers. No PGO or full-training claim.'}
(D/'SCREEN_512_SUMMARY.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)
