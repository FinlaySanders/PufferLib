from pathlib import Path
import json
import statistics
import subprocess
import time

r = Path(__file__).resolve().parent
expected = [x['label'] for x in json.loads((r/'MUON_FUSED_FULL.json').read_text())]
deadline = time.monotonic() + 600
while True:
    f = r/'MUON_FUSED_FULL.results.json'
    rows = json.loads(f.read_text()) if f.exists() else []
    if [x['label'] for x in rows] == expected:
        break
    assert time.monotonic() < deadline, 'Fused-Muon campaign incomplete; inspect the live process.'
    time.sleep(2)
reference = json.loads((r/'runs/combo_full_base_a/result.json').read_text())
base = statistics.mean(x['sps'] for x in rows if '_base_' in x['label'])
summary = dict(control_sps=base, rows=[])
for x in rows:
    assert x['rc']==0 and x['proofs']==reference['proofs'] and x['initial_sha']==x['final_sha']
    assert all(e['batch']==262144 and e['updates']==113 and e['mb']==4096 for e in x['epochs'])
    summary['rows'].append(dict(label=x['label'],sps=x['sps'],gain_percent=100*(x['sps']/base-1),
        tail_ms=1000*statistics.mean(e['rollout_tail'] for e in x['epochs'][64:79]),
        used_mib=max(e['used_mib'] for e in x['epochs']),proof_equal=True,actor_unchanged=True))
(r/'MUON_FUSED_FULL_SUMMARY.json').write_text(json.dumps(summary,indent=2))
print('FUSED FULL',json.dumps(summary),flush=True)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
subprocess.run(['python','campaign.py','BUFFER_CONFIRM.json'],cwd=r,check=True)
rows = json.loads((r/'BUFFER_CONFIRM.results.json').read_text())
base = statistics.mean(x['sps'] for x in rows if '_base_' in x['label'])
summary = dict(control_sps=base,configuration_experiment=True,rows=[])
for x in rows:
    assert x['rc']==0 and x['proofs']==reference['proofs'] and x['initial_sha']==x['final_sha']
    assert all(e['batch']==262144 and e['updates']==113 and e['mb']==4096 for e in x['epochs'])
    summary['rows'].append(dict(label=x['label'],sps=x['sps'],gain_percent=100*(x['sps']/base-1),
        tail_ms=1000*statistics.mean(e['rollout_tail'] for e in x['epochs'][64:79]),proof_equal=True,actor_unchanged=True))
(r/'BUFFER_CONFIRM_SUMMARY.json').write_text(json.dumps(summary,indent=2))
print('BUFFER CONFIRM',json.dumps(summary),flush=True)
