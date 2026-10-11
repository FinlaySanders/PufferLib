from pathlib import Path
import json
import statistics

r = Path(__file__).resolve().parent
rows = json.loads((r/'WORKER_COMBO.results.json').read_text())
expected = [x['label'] for x in json.loads((r/'WORKER_COMBO.json').read_text())]
assert [x['label'] for x in rows] == expected
reference = json.loads((r/'runs/combo_full_base_a/result.json').read_text())
base = statistics.mean(x['sps'] for x in rows if '_base_' in x['label'])
summary = dict(control_sps=base, configuration_experiment=True, rows=[])
for x in rows:
    assert x['rc']==0 and x['proofs']==reference['proofs'] and x['initial_sha']==x['final_sha']
    assert all(e['batch']==262144 and e['updates']==113 and e['mb']==4096 for e in x['epochs'])
    summary['rows'].append(dict(label=x['label'], sps=x['sps'], gain_percent=100*(x['sps']/base-1),
        tail_ms=1000*statistics.mean(e['rollout_tail'] for e in x['epochs'][64:79]),
        used_mib=max(e['used_mib'] for e in x['epochs']), proof_equal=True, actor_unchanged=True))
(r/'WORKER_COMBO_SUMMARY.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
