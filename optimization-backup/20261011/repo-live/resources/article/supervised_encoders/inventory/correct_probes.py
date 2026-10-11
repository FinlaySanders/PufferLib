from pathlib import Path
import subprocess,sys,json
r=Path('/puffertank/experiments/inventory-supervised-20260914');src=Path(__file__).resolve().parent
with (r/'probe_corrected.log').open('x') as f:
 p=subprocess.Popen([sys.executable,str(r/'benchmark_code_final/benchmark_corrected.py'),'--epochs','150'],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
 (r/'probe_corrected_active.json').write_text(json.dumps(dict(pid=p.pid)))
 rc=p.wait()
assert rc==0
subprocess.run([sys.executable,str(src/'summarize.py')],check=True)
(r/'BENCHMARK_DONE').write_text('constant-coordinate probe correction complete\n')
