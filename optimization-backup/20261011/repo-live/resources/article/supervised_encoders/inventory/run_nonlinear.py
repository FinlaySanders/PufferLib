from pathlib import Path
import subprocess,sys,shutil,json,hashlib
src=Path(__file__).resolve().parent;r=Path('/puffertank/experiments/inventory-supervised-20260914');code=r/'nonlinear_code';code.mkdir(exist_ok=False)
for name in ['benchmark.py','glyph_map.json','nonlinear.py']:shutil.copy2(src/name,code/name)
(code/'sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in code.iterdir()},indent=2))
with (r/'nonlinear.log').open('x') as f:
 p=subprocess.Popen([sys.executable,str(code/'nonlinear.py')],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
 (r/'nonlinear_active.json').write_text(json.dumps(dict(pid=p.pid)))
 rc=p.wait()
assert rc==0
(r/'NONLINEAR_DONE').write_text('ok\n')
