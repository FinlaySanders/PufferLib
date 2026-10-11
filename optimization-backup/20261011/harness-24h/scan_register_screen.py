from pathlib import Path
import json
import statistics
import subprocess
import time
import sys

r=Path(__file__).resolve().parent
pid=2905366
stat=Path('/proc')/str(pid)/'stat'
token=stat.read_text().split()[21] if stat.exists() else None
while stat.exists() and stat.read_text().split()[21]==token:
    time.sleep(2)
results=json.loads((r/'COMBO_FULL.results.json').read_text())
assert len(results)==6 and all(x['rc']==0 for x in results)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
rows=results[2:]
baseline=statistics.mean(x['sps'] for x in [rows[0],rows[-1]])
summary=[]
for x in rows:
    es=[e for e in x['epochs'] if 64<=e['epoch']<79]
    y=dict(label=x['label'],sps=x['sps'],gain_percent=100*(x['sps']/baseline-1),
        tail_ms=1000*statistics.mean(e['rollout_tail'] for e in es),
        proof_equal=x['proofs']==rows[0]['proofs'],actor_unchanged=x['initial_sha']==x['final_sha'])
    assert y['proof_equal'] and y['actor_unchanged']
    summary.append(y)
(r/'COMBO_SUMMARY.json').write_text(json.dumps(dict(control_sps=baseline,
    control_drift_percent=100*(rows[-1]['sps']/rows[0]['sps']-1),rows=summary),indent=2))
print('COMBINED FULL',summary,flush=True)
print('REGISTER SMOKE',flush=True)
if '--after-diagnostic' in sys.argv:
    diag=json.loads((r/'scan_register_diag_default/summary.json').read_text())
    nofma=json.loads((r/'scan_register_diag_nofma/summary.json').read_text())
    assert diag['cases']==54 and nofma['cases']==54
    assert nofma['forward_different']==nofma['backward_different']==0
    assert diag['max_forward_relative_l2']<0.002 and diag['max_backward_relative_l2']<0.002
    print('Using completed default/noFMA diagnostics; rounding differs, all finite.',flush=True)
else:
    subprocess.run(['python',str(r/'scan_register_smoke.py')],cwd=r,check=True)
print('BUILD REGISTER SCAN',flush=True)
with (r/'scan_regs_build.launcher.log').open('w') as f:
    subprocess.run(['python',str(r/'build.py'),'scan_regs_v14','-DPUF_MUON_OUTPLACE'],cwd=r,stdout=f,stderr=subprocess.STDOUT,check=True)
base={'PUF_CUDA_WAIT':'block'}
cases=[('regs_gpu_base_a',base)]
for tile in [2,4,8]:
    cases.append(('regs_gpu_tile'+str(tile),dict(base,PUF_SCAN_REGS=3,PUF_SCAN_REG_TILE=tile)))
cases += [('regs_gpu_forward',dict(base,PUF_SCAN_REGS=1,PUF_SCAN_REG_TILE=4)),
    ('regs_gpu_backward',dict(base,PUF_SCAN_REGS=2,PUF_SCAN_REG_TILE=4)),
    ('regs_gpu_row4',dict(base,PUF_SCAN_ROW=3,PUF_SCAN_TILE=4)),
    ('regs_gpu_base_b',base)]
jobs=[dict(kind='time',label=label,binary='scan_regs_v14',env=env,args=['--trials=4']) for label,env in cases]
(r/'SCAN_REGISTERS.json').write_text(json.dumps(jobs,indent=2))
subprocess.run(['python',str(r/'campaign.py'),'SCAN_REGISTERS.json'],cwd=r,check=True)
print('REGISTER SCREEN COMPLETE',flush=True)
