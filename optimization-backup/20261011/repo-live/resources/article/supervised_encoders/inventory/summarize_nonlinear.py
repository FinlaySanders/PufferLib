from pathlib import Path
import json,statistics as st,csv
root=Path('/puffertank/experiments/inventory-supervised-20260914/nonlinear_results');rows=[json.loads(p.read_text()) for p in root.glob('*.json') if p.name!='protocol.json'];assert len(rows)==72,len(rows)
out=Path(__file__).resolve().parent/'results';out.mkdir(exist_ok=True);cells=[]
for source in ['supervised_encoder','rl_policy']:
 for pool in ['max','sum','both']:
  for passed in [False,True]:
   for task in rows[0]['tasks']:
    values={}
    for kind in ['linear','mlp128_relu']:
     g=[d for d in rows if d['source']==source and d['pool']==pool and d['passthrough']==passed and d['head']==kind];assert len(g)==3
     a=[d['tasks'][task]['value'] for d in g];values[kind]=st.median(a) if all(x is not None for x in a) else None
    cells.append(dict(source=source,pool=pool,passthrough=passed,task=task,**values))
(out/'nonlinear_summary.json').write_text(json.dumps(dict(protocol=json.loads((root/'protocol.json').read_text()),cells=cells),indent=2)+'\n')
with (out/'nonlinear_summary.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(cells[0]));w.writeheader();w.writerows(cells)
