from pathlib import Path
import subprocess,json,hashlib,sys,shutil
root=Path(__file__).resolve().parent
repo=root.parents[2]
remote='/workspace/experiments/nethack-landmarks-20260914'
# Only completed result artifacts may trigger rendering.
code=f'''from pathlib import Path
import json,hashlib
r=Path({remote!r})
p=r/'results.json'
if not p.exists():raise SystemExit(3)
d=json.loads(p.read_text())
d['files']={{}}
for p in [r/'manifest.json',r/'engine.patch',r/'source.patch',r/'queue.jsonl',*r.glob('landmarks_s*.ep')]:
 d['files'][p.name]=p.read_text()
print(json.dumps(d))
'''
p=subprocess.run(['ssh','-o','ConnectTimeout=15','drone','python3 -'],input=code,text=True,capture_output=True)
if p.returncode:print('Completed landmark results not available yet.',file=sys.stderr);sys.exit(p.returncode)
d=json.loads(p.stdout);files=d.pop('files');raw=root/'results';raw.mkdir(exist_ok=True)
for name,content in files.items():assert Path(name).name==name;(raw/name).write_text(content)
assert sorted(r['seed'] for r in d['runs'])==list(range(801,809))
for run in d['runs']:
 p=raw/f"landmarks_s{run['seed']}.ep";rows=[list(map(int,l.split())) for l in p.read_text().splitlines() if l.strip()][4000:14000]
 assert len(rows)==run['n']==10000 and all(len(x)==15 for x in rows)
 for key,col in [('medusa',11),('castle',12)]:assert sum(x[col] for x in rows)==run[key]
 run['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
(raw/'summary.json').write_text(json.dumps(d,indent=2)+'\n')
roles=['All roles','Archeologist','Barbarian','Caveman','Healer','Knight','Monk','Priest','Rogue','Ranger','Samurai','Tourist','Valkyrie','Wizard']
stats=[dict(n=sum(r['n'] for r in d['runs']),medusa=sum(r['medusa'] for r in d['runs']),castle=sum(r['castle'] for r in d['runs']))]
for i in range(13):stats.append({k:sum(r['roles'][i][k] for r in d['runs']) for k in ('n','medusa','castle')})
h=['static const char *NAMES[14]={'+','.join(json.dumps(s) for s in roles)+'};']
for key in ('medusa','castle'):h.append('static const float '+key.upper()+'[14]={'+','.join(f'{100*s[key]/s["n"]:.8f}f' for s in stats)+'};')
(root/'data.h').write_text('\n'.join(h)+'\n')
subprocess.run(['clang','-O2','-I.','-I./raylib-5.5_linux_amd64/include','-I./src','-I./vendor','-Iresources',str(root/'plot.c'),'resources/trailer/fonts.c','-o',str(root/'plot'),'raylib-5.5_linux_amd64/lib/libraylib.a','-lGL','-lm','-lpthread','-DPLATFORM_DESKTOP'],cwd=repo,check=True)
subprocess.run(['xvfb-run','-a',str(root/'plot')],cwd=repo,check=True)
subprocess.run(['python3','resources/article/webify.py'],cwd=repo,check=True,stdout=subprocess.DEVNULL)
for rel in [rel for name in ('landmark_reach','landmark_reach_by_role') for rel in (f'{name}.png',f'web/{name}.png',f'web/{name}.jpg')]:
 dst=Path('/puffertank/docker/nethack_article')/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(repo/'resources/article/out'/rel,dst)
print(json.dumps(stats[0]))
