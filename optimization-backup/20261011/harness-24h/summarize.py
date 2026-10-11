from pathlib import Path
import json,statistics,sys
path=Path(sys.argv[1]);rows=json.loads(path.read_text())
base=[r for r in rows if 'base_' in r['label']]
if not base:base=rows[:1]
metric='sps' if 'sps' in rows[0] else 'mean_ms'
b=statistics.mean(r[metric] for r in base)
for r in rows:
 result={'label':r['label'],metric:r[metric],'speedup_pct':100*(r[metric]/b-1 if metric=='sps' else b/r[metric]-1)}
 if metric=='sps':
  es=[e for e in r['epochs'] if 64<=e['epoch']<79]
  result.update(tail_ms=statistics.mean(e['rollout_tail'] for e in es)*1000,memory_mib=max(e['used_mib'] for e in es),obs_equal=r['proofs']==base[0]['proofs'],frozen_equal=r['initial_sha']==r['final_sha'])
 print(json.dumps(result))
