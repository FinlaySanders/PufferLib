from pathlib import Path
import json,statistics,sys
p=Path(sys.argv[1]);rows=json.loads(p.read_text());bases=[r for r in rows if 'base_' in r['label']]
assert len(bases)>=2
b=statistics.mean(r['sps'] for r in bases)
summary={'control_sps':b,'control_drift_percent':100*(bases[-1]['sps']/bases[0]['sps']-1),'rows':[]}
ref=bases[0]
for r in rows:
 assert r['rc']==0 and len(r['proofs'])==80 and r['proofs']==ref['proofs'],r['label']
 assert r['initial_sha']==r['final_sha']==ref['initial_sha'],r['label']
 assert len(r['epochs'])==80
 assert all(e['batch']==262144 and e['mb']==4096 and e['updates']==113 for e in r['epochs'])
 es=[e for e in r['epochs'] if 64<=e['epoch']<79]
 early=[e for e in r['epochs'] if 3<=e['epoch']<15]
 summary['rows'].append({'label':r['label'],'sps':r['sps'],'gain_percent':100*(r['sps']/b-1),'tail_ms':1000*statistics.mean(e['rollout_tail'] for e in es),'memory_mib':max(e['used_mib'] for e in es),'early_sps':262144/statistics.mean(e['seconds'] for e in early)})
summary.update(observation_proofs_exact=True,frozen_actor_unchanged=True,scope='Frozen-actor replay throughput; not by itself an update-equivalence or learning-stability proof')
out=p.with_name(p.name.replace('.results.json','_SUMMARY.json'));out.write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
