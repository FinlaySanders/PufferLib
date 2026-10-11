from pathlib import Path
import json,statistics as st,hashlib,subprocess,shutil
here=Path(__file__).resolve().parent;repo=here.parents[3]
root=Path('/puffertank/experiments/inventory-supervised-20260914/results')
rows=[];sources=[]
for p in sorted(root.glob('supervised_*.json')):
 rows.append(json.loads(p.read_text()));sources.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
assert len(rows)==18
keys=['n_items','max_known_enchant','wield_enchant'];pools=['max','sum','both'];vals=[]
for key in keys:
 table=[]
 for pool in pools:
  pair=[]
  for passed in [False,True]:
   group=[d for d in rows if d['pool']==pool and d['passthrough']==passed];assert sorted(d['seed'] for d in group)==[1,2,3]
   pair.append(st.median(d['tasks'][key]['value'] for d in group))
  table.append(pair)
 vals.append(table)
data=dict(tasks=keys,pools=pools,pass_order=[False,True],metric='test R2',aggregation='median of 3 fit seeds',values=vals,sources=sources)
(here/'supervised_figure_data.json').write_text(json.dumps(data,indent=2)+'\n')
(here/'supervised_figure_data.h').write_text('static const float VALUE[3][3][2] = '+json.dumps(vals).replace('[','{').replace(']','}')+';\n')
subprocess.run(['clang','-O2','-I.','-I./raylib-5.5_linux_amd64/include','-I./src','-I./vendor','-Iresources',str(here/'supervised_figure.c'),'resources/trailer/fonts.c','-o',str(here/'supervised_figure'),'raylib-5.5_linux_amd64/lib/libraylib.a','-lGL','-lm','-lpthread','-DPLATFORM_DESKTOP'],cwd=repo,check=True)
subprocess.run(['xvfb-run','-a',str(here/'supervised_figure')],cwd=repo,check=True)
subprocess.run(['python3','resources/article/webify.py'],cwd=repo,check=True,stdout=subprocess.DEVNULL)
for rel in ['inventory_encoder_supervised.png','web/inventory_encoder_supervised.png','web/inventory_encoder_supervised.jpg']:
 shutil.copy2(repo/'resources/article/out'/rel,Path('/puffertank/docker/nethack_article')/rel)
