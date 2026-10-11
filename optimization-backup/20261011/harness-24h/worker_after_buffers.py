from pathlib import Path
import json
import subprocess
import time

r=Path(__file__).resolve().parent
deadline=time.monotonic()+900
while not (r/'BUFFER_CONFIRM_SUMMARY.json').exists():
    assert time.monotonic()<deadline, 'Buffer confirmation incomplete; inspect the live process.'
    time.sleep(2)
summary=json.loads((r/'BUFFER_CONFIRM_SUMMARY.json').read_text())
assert len(summary['rows'])==4 and all(x['proof_equal'] and x['actor_unchanged'] for x in summary['rows'])
print('Buffer confirmation complete; starting native worker-count screen',flush=True)
subprocess.run(['python','worker_count_screen.py'],cwd=r,check=True)
