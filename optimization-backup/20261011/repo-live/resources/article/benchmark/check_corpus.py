import subprocess,os,json
from pathlib import Path
root=Path(__file__).resolve().parents[3]; b=Path(__file__).resolve().parent
engines={'stock':('/puffertank/nle-stock/nle/libnethack.so','/puffertank/nle-stock/nle/nethackdir'),'fast':(str(root/'vendor/fast-nle/build/libnethack.so'),str(root/'vendor/fast-nle/build/dat'))}
env=dict(os.environ,LD_PRELOAD=str(b/'faketime.so'),NLE_FAKE_TIME='1600000000',TZ='UTC')
out=[]
for g in sorted((root/'vendor/fast-nle/tests/goldens').glob('*.golden')):
 traces={};rc={}
 for kind,(lib,dat) in engines.items():
  p=subprocess.run([str(b/f'engine_{kind}'),lib,dat,str(g),'1','5000','0',str(b/f'{kind}.trace')],env=env,capture_output=True,text=True,timeout=30)
  traces[kind]=[l.split() for l in (b/f'{kind}.trace').read_text().splitlines()];rc[kind]=p.returncode
 a,c=traces.values();count=min(len(a),len(c))
 full=next((i for i in range(count) if a[i]!=c[i]),count)
 bl=next((i for i in range(count) if a[i][2:]!=c[i][2:]),count)
 row=dict(file=g.name,keys=count,full_match_prefix=full,blstats_match_prefix=bl,rc=rc);out.append(row);print(json.dumps(row),flush=True)
(b/'corpus_check.json').write_text(json.dumps(out,indent=2))
