from pathlib import Path
import json,csv,statistics as st
r=Path('/puffertank/experiments/inventory-supervised-20260914/results')
out=Path(__file__).resolve().parent/'results';out.mkdir(exist_ok=True)
rows=[json.loads(p.read_text()) for p in r.glob('*.json') if p.name!='protocol.json']
assert len(rows)==36,(len(rows),'waiting for 6 arms x 3 seeds x 2 modes')
assert len({(x['mode'],x['pool'],x['passthrough'],x['seed']) for x in rows})==36
names=list(rows[0]['tasks']);cells=[]
for pool in ['max','sum','both']:
 for passed in [False,True]:
  for task in names:
   groups={mode:[x for x in rows if x['mode']==mode and x['pool']==pool and x['passthrough']==passed] for mode in ['supervised','frozen']}
   assert all(len(v)==3 for v in groups.values())
   scores={k:[x['tasks'][task]['value'] for x in v if x['tasks'][task]['value'] is not None] for k,v in groups.items()}
   med={k:st.median(v) if len(v)==3 else None for k,v in scores.items()}
   metric=groups['supervised'][0]['tasks'][task]['metric'];floor=.5 if metric=='auc' else 0
   ratio=None
   if med['supervised'] is not None and med['frozen'] is not None and med['supervised']-floor>.1:ratio=(med['frozen']-floor)/(med['supervised']-floor)
   cells.append(dict(pool=pool,passthrough=passed,task=task,metric=metric,supervised=med['supervised'],frozen=med['frozen'],relative_decodability=ratio,supervised_seeds=scores['supervised'],frozen_seeds=scores['frozen'],test_n=groups['supervised'][0]['tasks'][task]['n']))
report=dict(protocol=json.loads((r/'protocol.json').read_text()),cells=cells)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
with (out/'summary.csv').open('w') as f:
 cols=['pool','passthrough','task','metric','supervised','frozen','relative_decodability','test_n'];w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(cells)
title='# Inventory encoder experiments' if report['protocol']['epochs']>30 else '# Pilot inventory experiments — final comparison pending'
md=[title,'','Three-seed medians on held-out games. AUC for binary targets; R² for regression.','Relative decodability is the gain above the baseline divided by the supervised gain;','it is not the fraction of all information retained or evidence of causal policy use.','','| Target | Pool | Pass | Supervised | Frozen policy | Relative decodability |','|---|---|---|---:|---:|---:|']
for c in cells:
 fmt=lambda x:'—' if x is None else f'{x:.3f}'
 md.append(f"| {c['task']} | {c['pool']} | {c['passthrough']} | {fmt(c['supervised'])} | {fmt(c['frozen'])} | {fmt(c['relative_decodability'])} |")
(out/'RESULTS.md').write_text('\n'.join(md)+'\n')
print(out/'RESULTS.md')
