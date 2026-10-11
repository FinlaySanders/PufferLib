import json,sys,statistics
from pathlib import Path
root=Path(sys.argv[1])
config=json.loads((root/'config.json').read_text())
rows=[]
for p in root.glob('w*.jsonl'):
    for line in p.read_text().splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: pass
expected=config['workers']*config['episodes_per_worker']
valid=[r for r in rows if r.get('completed') and 'error' not in r]
complete=len(valid)==expected and {(r['worker'],r['episode']) for r in valid}=={(w,e) for w in range(config['workers']) for e in range(1,config['episodes_per_worker']+1)}
result=dict(attempted=len(rows),completed=len(valid),expected=expected,certificate_complete=complete,errors=[r for r in rows if not r.get('completed') or 'error' in r])
if complete:
    scores=[r['env_score'] for r in valid]
    result.update(mean=statistics.mean(scores),median=statistics.median(scores),min=min(scores),max=max(scores))
print(json.dumps(result,indent=2))
