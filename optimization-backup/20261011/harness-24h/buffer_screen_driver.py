from pathlib import Path
import json
import statistics
import subprocess
import time

r=Path(__file__).resolve().parent
# Wait for the known profile/build/native-screen process, not a log line.
stat=Path('/proc/2909156/stat')
token=stat.read_text().split()[21] if stat.exists() else None
while stat.exists() and stat.read_text().split()[21]==token:
    time.sleep(2)
native=json.loads((r/'current_workload_pgo/native.json').read_text())
assert len(native)>=2
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
base=statistics.mean(x['sps'] for x in native if '_base_' in x['label'])
candidate=statistics.mean(x['sps'] for x in native if '_candidate_' in x['label'])
gain=100*(candidate/base-1)
(r/'current_workload_pgo/summary.json').write_text(json.dumps(dict(control_sps=base,candidate_sps=candidate,gain_percent=gain,
    native=native,source_unchanged=True,decision='park below firstpair gate' if len(native)==2 else 'paired native screen complete; evaluate followup'),indent=2))
print('PGO SCREEN',base,candidate,gain,flush=True)
jobs=json.loads((r/'BUFFER_SCREEN.json').read_text())
reference=json.loads((r/'runs/combo_full_base_a/result.json').read_text())
smoke_reference=json.loads((r/'runs/combo_smoke/result.json').read_text())
results=[]
for job in jobs:
    label=job['label'];print('START',label,flush=True)
    cmd=['python',str(r/'run.py'),'full',label,'--binary='+str(r/'binaries'/job['binary'])]
    cmd+=['--env='+k+'='+str(v) for k,v in job['env'].items()]+job['args']
    if not (r/'runs'/label/'result.json').exists():
        with (r/(label+'.launcher.log')).open('w') as f:
            subprocess.run(cmd,cwd=r,stdout=f,stderr=subprocess.STDOUT,check=True)
    x=json.loads((r/'runs'/label/'result.json').read_text())
    expected=smoke_reference if len(x['proofs'])==4 else reference
    assert x['rc']==0 and x['proofs']==expected['proofs']
    assert x['initial_sha']==x['final_sha']
    assert all(e['batch']==262144 and e['updates']==113 and e['mb']==4096 for e in x['epochs'])
    results.append(x)
    (r/'BUFFER_SCREEN.results.json').write_text(json.dumps(results,indent=2))
    print('DONE',label,x['sps'],flush=True)
print('BUFFER CONFIGURATION SCREEN COMPLETE',flush=True)
