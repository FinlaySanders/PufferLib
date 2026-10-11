from pathlib import Path
import json
from native_pool.snapshot_test import run
r=Path(__file__).resolve().parent
engine='/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build'
binary=r/'native_pool/snapshot_horizon'
smoke=run('horizon_smoke',512,'0:256,20:256,21:256',engine=engine,workers=32,pin=False,warm=256,binary_override=binary)
assert smoke['endpoints_ok']
full=run('focus32_horizon_aligned',2048,'0:1920,1:1920,20:1920,21:1920,0:1920',engine=engine,workers=32,pin=False,warm=8320,binary_override=binary)
assert full['endpoints_ok']
assert all(x['result']['obs']=='b97835c62aaf388f'for x in full['cases'])
(r/'NATIVE_HORIZON_STUDY.json').write_text(json.dumps({'smoke':smoke,'full':full},indent=2))
