from pathlib import Path
import json,statistics as st,hashlib,subprocess,shutil,argparse
p=argparse.ArgumentParser();p.add_argument('--stage',choices=['supervised_and_linear','nonlinear'],required=True);args=p.parse_args()
here=Path(__file__).resolve().parent;repo=here.parents[4];root=Path('/puffertank/experiments/inventory-concrete-20260914')
keys=['arrow_quantity','best_armor_enchant','wielding_bow'];sources=[]
if args.stage=='supervised_and_linear':
 files=sorted((root/'results').glob('supervised_*.json'));assert len(files)==18
 rows=[json.loads(f.read_text()) for f in files];vals=[]
 for key in keys:
  table=[]
  for pool in ['max','sum','both']:
   pair=[]
   for passed in [False,True]:
    group=[d for d in rows if d['pool']==pool and d['passthrough']==passed];assert sorted(d['seed'] for d in group)==[1,2,3]
    pair.append(st.median(d['tasks'][key]['value'] for d in group))
   table.append(pair)
  vals.append(table)
 header='figure_data.h';symbol='VALUE';cfile='architecture.c';outfile='inventory_encoder_supervised_concrete'
else:
 files=sorted((root/'nonlinear_results').glob('*.json'));files=[p for p in files if p.name!='protocol.json'];assert len(files)==12
 rows=[json.loads(f.read_text()) for f in files];vals=[]
 for key in keys:
  table=[]
  for source in ['supervised_encoder','rl_policy']:
   pair=[]
   for head in ['linear','mlp128_relu']:
    group=[d for d in rows if d['source']==source and d['head']==head];assert sorted(d['seed'] for d in group)==[1,2,3]
    pair.append(st.median(d['tasks'][key]['value'] for d in group))
   table.append(pair)
  vals.append(table)
 header='probe_data.h';symbol='PROBE';cfile='probes.c';outfile='inventory_encoder_probes_concrete'
for f in files:sources.append(dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
(here/(outfile+'.json')).write_text(json.dumps(dict(tasks=keys,values=vals,metrics=['r2','r2','auc'],sources=sources),indent=2)+'\n')
(here/header).write_text('static const float '+symbol+f'[3][{len(vals[0])}][2] = '+json.dumps(vals).replace('[','{').replace(']','}')+';\n')
# Archive exact fit metadata in the article as well as the experiment directory.
out=here/'results'/args.stage;out.mkdir(parents=True,exist_ok=True)
for f in files:shutil.copy2(f,out/f.name)
subprocess.run(['clang','-O2','-I.','-I./raylib-5.5_linux_amd64/include','-I./src','-I./vendor','-Iresources',str(here/cfile),'resources/trailer/fonts.c','-o',str(here/'renderer'),'raylib-5.5_linux_amd64/lib/libraylib.a','-lGL','-lm','-lpthread','-DPLATFORM_DESKTOP'],cwd=repo,check=True)
subprocess.run(['xvfb-run','-a',str(here/'renderer')],cwd=repo,check=True)
subprocess.run(['python3','resources/article/webify.py'],cwd=repo,check=True,stdout=subprocess.DEVNULL)
for rel in [f'{outfile}.png',f'web/{outfile}.png',f'web/{outfile}.jpg']:shutil.copy2(repo/'resources/article/out'/rel,Path('/puffertank/docker/nethack_article')/rel)
print(outfile,vals,flush=True)
