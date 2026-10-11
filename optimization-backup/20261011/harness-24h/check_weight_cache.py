from pathlib import Path
import json
import os
import subprocess
import sys
import time

R=Path(__file__).resolve().parent;D=R/'weight_cache'
OLD=Path('/puffertank/experiments/nethack-compact-state-20261008')
clean={k:v for k,v in os.environ.items() if not k.startswith(('NH_','NLE_','OMP_','PUF_','PUFFER_','CPU_')) and k not in ('LD_LIBRARY_PATH','LD_PRELOAD','NETHACKOPTIONS')}
clean.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat',NH_ZT_MASK='0')
gold=sorted(map(str,(OLD/'checks/goldens').glob('*.golden')))
fuzz=sorted(map(str,(OLD/'checks/fuzz').glob('*.golden')))
assert len(gold)==34 and len(fuzz)==26
rows=[]
for variant in ['verify','build']:
    for label,exe,args,extra in [('golden','replay_golden',gold,{}),('fuzz','replay_golden',fuzz,{}),('status','replay_golden',gold,{'NLE_REPLAY_OPTIONS_APPEND':',!status_updates'}),('interleaved','replay_multi',gold,{}),('shuffled','replay_multi',gold,{})]:
        cmd=['/puffertank/experiments/nethack-perf-20260917/gates/'+exe]+(['--'+label] if exe=='replay_multi' else [])+[str(D/variant/'libnethack.so'),clean['NETHACKDIR'],*args]
        start=time.monotonic();pfx=variant+'_'+label
        print('CHECK',pfx,flush=True)
        with (D/(pfx+'.log')).open('w') as f:
            p=subprocess.run(cmd,env=dict(clean,**extra),stdout=f,stderr=subprocess.STDOUT)
        rows.append({'variant':variant,'label':label,'rc':p.returncode,'seconds':time.monotonic()-start,'command':cmd})
        (D/'QUICK_GATES.json').write_text(json.dumps(rows,indent=2))
        assert p.returncode==0,(D/(pfx+'.log')).read_text()[-5000:]
        print('PASS',pfx,round(time.monotonic()-start,2),flush=True)
sys.path.insert(0,str(R/'native_pool'))
from snapshot_test import run
row=run('weight_cache_verify512',512,'0:2048',engine=D/'verify',workers=32,pin=False)
print('WARM AND MATURE CACHE VERIFICATION PASSED',flush=True)
