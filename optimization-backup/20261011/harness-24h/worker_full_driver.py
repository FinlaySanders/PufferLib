from pathlib import Path
import json
import statistics
import subprocess
import time

r=Path(__file__).resolve().parent
deadline=time.monotonic()+300
while not (r/'WORKER_COUNT_SUMMARY.json').exists():
    assert time.monotonic()<deadline, 'Native worker screen incomplete; inspect it.'
    time.sleep(2)
native=json.loads((r/'WORKER_COUNT_SUMMARY.json').read_text())
assert all(x['endpoint_equal'] for x in native['rows'])
assert max(x['gain_percent'] for x in native['rows'])>1.0
subprocess.run(['python','campaign.py','WORKER_FULL.json'],cwd=r,check=True)
rows=json.loads((r/'WORKER_FULL.results.json').read_text())
base=statistics.mean(x['sps'] for x in rows if '_base_' in x['label'])
reference=json.loads((r/'runs/combo_full_base_a/result.json').read_text())
summary=dict(control_sps=base,configuration_experiment=True,rows=[])
for x in rows:
    assert x['rc']==0 and x['proofs']==reference['proofs'] and x['initial_sha']==x['final_sha']
    assert all(e['batch']==262144 and e['updates']==113 and e['mb']==4096 for e in x['epochs'])
    summary['rows'].append(dict(label=x['label'],sps=x['sps'],gain_percent=100*(x['sps']/base-1),
        tail_ms=1000*statistics.mean(e['rollout_tail'] for e in x['epochs'][64:79]),proof_equal=True,actor_unchanged=True))
(r/'WORKER_FULL_SUMMARY.json').write_text(json.dumps(summary,indent=2))
print('FULL WORKER SCREEN',json.dumps(summary),flush=True)
