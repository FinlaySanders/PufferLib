from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

root = Path(__file__).resolve().parent
source = root / 'clean_wait/source'
target = root / 'binaries/clean_wait'
assert not target.exists()
assert not subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid',
    '--format=csv,noheader'], text=True).strip()
flags = (root / 'build_flags.txt').read_text().strip()
command = ['./build.sh', 'nethack', 'puffer_clean_wait']
start = time.time()
with (root / 'clean_wait/build.log').open('w') as log:
    result = subprocess.run(command, cwd=source, env=dict(os.environ, NVCC_EXTRA=flags),
        stdout=log, stderr=subprocess.STDOUT)
metadata = dict(command=command, flags=flags, rc=result.returncode, seconds=time.time()-start)
if result.returncode == 0:
    data = (source / 'puffer_clean_wait').read_bytes()
    metadata['binary_sha256'] = hashlib.sha256(data).hexdigest()
    target.write_bytes(data)
    target.chmod(0o755)
(root / 'clean_wait/build.json').write_text(json.dumps(metadata, indent=2))
print(metadata)
if result.returncode:
    print((root / 'clean_wait/build.log').read_text()[-6000:])
raise SystemExit(result.returncode)
