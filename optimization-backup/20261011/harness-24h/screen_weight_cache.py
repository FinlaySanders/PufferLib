from pathlib import Path
import json
import statistics
import sys

R=Path(__file__).resolve().parent;D=R/'weight_cache'
sys.path.insert(0,str(R/'native_pool'))
from snapshot_test import run
envs=int(sys.argv[1]) if len(sys.argv)>1 else 512
steps=2048 if envs==512 else 512
assert envs in (512,2048)
rows=[]
for role,engine in [('base_a',R/'floor_empty_base/build'),('candidate_a',D/'build'),('candidate_b',D/'build'),('base_b',R/'floor_empty_base/build')]:
    row=run('weight_cache_'+str(envs)+'_'+role,envs,f'0:{steps},0:{steps}',engine=engine,workers=32,pin=False)
    row['role']=role;rows.append(row)
    (D/f'SCREEN_{envs}.json').write_text(json.dumps(rows,indent=2))
base=[float(c['result']['sps']) for row in rows if row['role'].startswith('base') for c in row['cases']]
candidate=[float(c['result']['sps']) for row in rows if row['role'].startswith('candidate') for c in row['cases']]
summary={'control_sps':statistics.mean(base),'candidate_sps':statistics.mean(candidate),'gain_percent':100*(statistics.mean(candidate)/statistics.mean(base)-1),'control_drift_percent':100*(statistics.mean(base[2:])/statistics.mean(base[:2])-1),'control_values':base,'candidate_values':candidate,'endpoints_ok':all(row['endpoints_ok'] for row in rows),'scope':f'Ordinary LTO native replay,{envs}env/32workers. Not retained: broader invalidation audit, PGO and full-training checks still required.'}
(D/f'SCREEN_{envs}_SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
