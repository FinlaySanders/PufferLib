from pathlib import Path
import time,subprocess,sys
root=Path('/puffertank/experiments/inventory-supervised-20260914')
while not (root/'NONLINEAR_DONE').exists():time.sleep(20)
subprocess.run([sys.executable,str(Path(__file__).with_name('summarize_nonlinear.py'))],check=True)
