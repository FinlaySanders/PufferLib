from pathlib import Path
import time,subprocess,shutil,json,sys,hashlib
root=Path('/puffertank/experiments/inventory-supervised-20260914');src=Path(__file__).resolve().parent
while not (root/'BENCHMARK_DONE').exists():time.sleep(10)
assert len(list((root/'results').glob('*.pt')))==36
# Keep the first fixed-budget pass as pilot evidence, not the final ceiling.
(root/'results').rename(root/'results_30epochs')
(root/'BENCHMARK_DONE').rename(root/'PILOT_DONE')
code=root/'benchmark_code_final';code.mkdir(exist_ok=False)
for name in ['benchmark.py','glyph_map.json','summarize.py']:shutil.copy2(src/name,code/name)
(code/'sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in code.iterdir()},indent=2))
with (root/'benchmark_final.log').open('x') as f:
 p=subprocess.Popen([sys.executable,str(code/'benchmark.py'),'--epochs','150'],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
 (root/'benchmark_final_active.json').write_text(json.dumps(dict(pid=p.pid)))
 rc=p.wait()
assert rc==0,rc
subprocess.run([sys.executable,str(src/'summarize.py')],check=True)
(root/'BENCHMARK_DONE').write_text('final 150-epoch budget\n')
