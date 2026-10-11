from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
label = sys.argv[1]
source = root / 'source'
snapshot = root / 'snapshots' / label
snapshot.mkdir(parents=True,exist_ok=False)
for name in ['src/pufferl.cu','src/algo.cu','src/pipeline_bench.cuh','src/env_pool.h','src/env_pages.h','src/rec_lt.cuh','src/train_dw_lt.cuh','src/rec_fused.cuh','src/inventory_fused.cuh','src/entity_fused.cuh','src/entity_train_fused.cuh','ocean/nethack/nethack.cu','ocean/nethack/pool_bwd.cuh','ocean/nethack/embedding_reduce.cuh','ocean/nethack/pass_fast.cuh','ocean/nethack/sfeat_fast.cuh']:
    dest=snapshot/name
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source/name,dest)
flags = (root / 'build_flags.txt').read_text().strip() + ' ' + ' '.join(sys.argv[2:])
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
command = ['./build.sh', 'nethack', 'puffer_' + label]
start = time.time()
with (root / (label + '-build.log')).open('w') as log:
    result = subprocess.run(command,cwd=source,env=dict(os.environ,NVCC_EXTRA=flags),stdout=log,stderr=subprocess.STDOUT)
metadata = dict(command=command,flags=flags,rc=result.returncode,seconds=time.time()-start,
    source_hashes={str(p.relative_to(snapshot)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(snapshot.rglob('*')) if p.is_file()})
if result.returncode == 0:
    binary = source / ('puffer_' + label)
    metadata['binary_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
    target = root / 'binaries' / label
    assert not target.exists()
    target.write_bytes(binary.read_bytes());target.chmod(0o755)
(root / (label + '-build.json')).write_text(json.dumps(metadata,indent=2))
print(metadata)
if result.returncode:
    print((root/(label+'-build.log')).read_text()[-6000:])
raise SystemExit(result.returncode)
