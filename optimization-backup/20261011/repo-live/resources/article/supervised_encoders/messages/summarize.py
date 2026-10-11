from pathlib import Path
import json,statistics,hashlib
r=Path('/puffertank/experiments/message-supervised-20260914');out=Path('/puffertank/pufferlib/resources/article/supervised_encoders/messages')
assert (r/'DONE').exists(),'Fits incomplete'
rows=[json.loads(p.read_text()) for p in sorted(r.glob('*_s*.json'))];assert len(rows)==36
primary=['you_kill','you_hit','enemy_hits','enemy_miss','item_found']
summary=[]
for kind,v,d in sorted(set((x['kind'],x['buckets'],x['width']) for x in rows)):
 g=[x for x in rows if (x['kind'],x['buckets'],x['width'])==(kind,v,d)]
 metrics={}
 for task in g[0]['tasks']:
  metric='auc' if 'auc' in g[0]['tasks'][task] else 'accuracy';values=[x['tasks'][task][metric] for x in g]
  metrics[task]={metric:statistics.median(values) if all(v is not None for v in values) else None,'seed_values':values,'n':g[0]['tasks'][task]['n']}
 summary.append(dict(kind=kind,buckets=v,width=d,parameters=g[0]['parameters'],primary_macro_auc=statistics.median([statistics.mean(x['tasks'][t]['auc'] for t in primary) for x in g]),tasks=metrics))
(out/'results.json').write_text(json.dumps(dict(primary_tasks=primary,rows=summary,protocol=json.loads((r/'protocol.json').read_text()),source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in r.glob('*_s*.json')}),indent=2))
lines=['# Supervised message results','', 'Medians over three initialization seeds. Primary macro AUROC averages the five event tasks with at least 30 positives and negatives in the test split. Related message templates may cross splits; this is not a held-out-game evaluation.','', '| Encoder | Buckets | Width | Parameters | Primary macro AUROC |','|---|---:|---:|---:|---:|']
for x in summary:lines.append(f"| {x['kind']} | {x['buckets'] or '—'} | {x['width']} | {x['parameters']} | {x['primary_macro_auc']:.4f} |")
lines.extend(['','Individual tasks and all seed values are in results.json. Prayer has no examples and is unscored; hunger, condition, experience and species evaluations have small test samples.',''])
(out/'RESULTS.md').write_text('\n'.join(lines));print('\n'.join(lines))
