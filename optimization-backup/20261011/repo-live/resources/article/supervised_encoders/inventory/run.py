from pathlib import Path
import subprocess,json,shutil,hashlib,sys
src=Path(__file__).resolve().parent
root=Path('/puffertank/experiments/inventory-supervised-20260914')
assert (root/'CAPTURE_DONE').exists()
assert len(list((root/'smoke_results').glob('*.pt')))==2
# Freeze the implementation before launching a detached experiment.
code=root/'benchmark_code';code.mkdir(exist_ok=False)
for name in ['benchmark.py','glyph_map.json','summarize.py']:
 shutil.copy2(src/name,code/name)
(code/'sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in code.iterdir()},indent=2))
with (root/'benchmark.log').open('x') as f:
 child=subprocess.Popen([sys.executable,str(code/'benchmark.py')],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
 (root/'benchmark_active.json').write_text(json.dumps(dict(pid=child.pid)))
 rc=child.wait()
assert rc==0,rc
# The summarizer's output is rooted in the article directory.
subprocess.run([sys.executable,str(src/'summarize.py')],check=True)
(root/'BENCHMARK_DONE').write_text('ok\n')
