from pathlib import Path
import json,hashlib,statistics,subprocess,sys,time
r=Path(__file__).resolve().parent
# Explicitly gate on the current live campaign child and completed artifacts.
a=json.loads((r/'ACTIVE.json').read_text());assert a.get('label')=='pass_full_base_b',a
pid=a['pid'];proc=Path('/proc')/str(pid)
assert proc.exists() and (proc/'comm').read_text().strip()=='pass_fast_v16'
while proc.exists():time.sleep(2)
for _ in range(5):
 if (r/'runs/pass_full_base_b/result.json').exists():break
 time.sleep(1)
rows=json.loads((r/'PASS_FAST_FULL.results.json').read_text())
assert len(rows)==3
ref=json.loads((r/'runs/combo_full_base_a/result.json').read_text())
base=statistics.mean(x['sps'] for x in rows if 'base_' in x['label'])
out=[]
for x in rows:
 assert x['rc']==0 and x['proofs']==ref['proofs'] and x['initial_sha']==x['final_sha']
 ep=[z for z in x['epochs'] if 64<=z['epoch']<=78]
 assert all(z['batch']==262144 and z['mb']==4096 and z['updates']==113 for z in ep)
 out.append(dict(label=x['label'],sps=x['sps'],gain_percent=100*(x['sps']/base-1),tail_ms=1000*statistics.mean(z['rollout_tail'] for z in ep)))
summary=dict(control_sps=base,control_drift_percent=100*(rows[-1]['sps']/rows[0]['sps']-1),rows=out,observation_proofs_exact=True,frozen_actor_unchanged=True,status='Screen only; no full training proof')
(r/'PASS_FAST_FULL_SUMMARY.json').write_text(json.dumps(summary,indent=2))
print('PASS_FULL',summary,flush=True)
with (r/'LEDGER.md').open('a') as f:f.write('\nPass metadata full screen: '+json.dumps(summary)+'\n')
for command in [[sys.executable,'sfeat_fast_smoke.py'],[sys.executable,'build.py','sfeat_fast_v17','-DPUF_MUON_OUTPLACE'],[sys.executable,'campaign.py','SFEAT_FAST_SCREEN.json']]:
 print('START',command,flush=True);subprocess.run(command,cwd=r,check=True)
