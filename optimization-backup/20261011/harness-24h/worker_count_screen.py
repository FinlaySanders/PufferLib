from pathlib import Path
import importlib.util
import json
import statistics
import subprocess

r = Path(__file__).resolve().parent
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
spec=importlib.util.spec_from_file_location('native_snapshot',r/'native_pool/snapshot_test.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
engine='/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build'
results=[]
endpoint=None
for label,workers in [('workers24_base_a',24),('workers20_native',20),('workers28_native',28),('workers32_native',32),('workers24_base_b',24)]:
    x=module.run(label,2048,'0:512,0:512',engine=engine,workers=workers,pin=False)
    for c in x['cases']:
        e=tuple(c['result'][k] for k in ['obs','turns','age'])
        if endpoint is None:endpoint=e
        assert e==endpoint,(label,e,endpoint)
    result=dict(label=label,workers=workers,pinned=False,
        sps=statistics.mean(float(c['result']['sps']) for c in x['cases']),
        endpoint_equal=True,result_path=str(r/'native_pool/runs'/label/'result.json'))
    results.append(result)
    (r/'WORKER_COUNT.results.json').write_text(json.dumps(results,indent=2))
base=statistics.mean(x['sps'] for x in results if '_base_' in x['label'])
for x in results:x['gain_percent']=100*(x['sps']/base-1)
summary=dict(control_sps=base,configuration_experiment=True,rows=results)
(r/'WORKER_COUNT_SUMMARY.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2),flush=True)
