from pathlib import Path
import json
import subprocess
import time

r = Path(__file__).resolve().parent
expected = [x['label'] for x in json.loads((r/'BUFFER_SCREEN.json').read_text())]
deadline = time.monotonic() + 600
while True:
    results = json.loads((r/'BUFFER_SCREEN.results.json').read_text())
    if [x['label'] for x in results] == expected:
        assert all(x['rc'] == 0 for x in results)
        break
    assert time.monotonic() < deadline, 'Buffer campaign did not finish; inspect it before continuing.'
    time.sleep(2)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'], text=True).strip()
for command in [
    ['python', 'muon_fused_smoke.py'],
    ['python', 'build.py', 'muon_fused_v15', '-DPUF_MUON_OUTPLACE'],
    ['python', 'campaign.py', 'MUON_FUSED_GPU.json'],
]:
    print('START', command, flush=True)
    subprocess.run(command, cwd=r, check=True)
    print('DONE', command, flush=True)
