import json,sys,statistics,collections
from pathlib import Path
root=Path(sys.argv[1]);config=json.loads((root/'config.json').read_text())
rows=[]
for p in root.glob('w*.jsonl'):
    for line in p.read_text().splitlines():
        try:rows.append(json.loads(line))
        except json.JSONDecodeError:pass
expected={(w,e) for w in range(config['workers']) for e in range(1,config['episodes_per_worker']+1)}
seen=[(r['worker'],r['episode']) for r in rows]
complete=set(seen)==expected and len(seen)==len(expected) and all('env_score' in r and r.get('outcome')!='infrastructure_error' for r in rows)
result=dict(attempts_recorded=len(rows),expected=len(expected),attempt_set_complete=complete,outcomes=dict(collections.Counter(r.get('outcome') for r in rows)),environment_completions=sum(r.get('completed',False) for r in rows),duplicate_rows=len(seen)-len(set(seen)))
if complete:
    scores=[r['env_score'] for r in rows]
    conservative=[r['env_score'] if r.get('completed') else 0 for r in rows]
    result.update(mean=statistics.mean(scores),median=statistics.median(scores),mean_with_incomplete_as_zero=statistics.mean(conservative),median_with_incomplete_as_zero=statistics.median(conservative))
print(json.dumps(result,indent=2))
