from pathlib import Path
import subprocess,sys,shutil,hashlib,json
src=Path(__file__).resolve().parent;r=Path('/puffertank/experiments/inventory-concrete-20260914');code=r/'code';code.mkdir(exist_ok=False)
for name in ['benchmark.py','glyph_map.json','nonlinear.py']:shutil.copy2(src/name,code/name)
(code/'sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in code.iterdir()},indent=2))
for script,args,stage in [('benchmark.py',['--epochs','150'],'supervised_and_linear'),('nonlinear.py',[],'nonlinear')]:
 with (r/(stage+'.log')).open('x') as f:
  p=subprocess.Popen([sys.executable,str(code/script),*args],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
  (r/'active.json').write_text(json.dumps(dict(stage=stage,pid=p.pid)))
  print('START',stage,p.pid,flush=True);rc=p.wait()
 assert rc==0,(stage,rc)
 (r/(stage+'_DONE')).write_text('ok\n')
 print('DONE',stage,flush=True)
 subprocess.run([sys.executable,str(src/'render.py'),'--stage',stage],check=True)
(r/'DONE').write_text('ok\n')
