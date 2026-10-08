from pathlib import Path
import json,re
r=Path(__file__).resolve().parent;out={'kernel':[],'training':[]}
for name,file in [('score20','test.log'),('identify21','test-depth.log')]:
 s=(r/file).read_text();assert 'PASS all bit-exact' in s
 for B in [128,512]:
  a=[(int(k),float(t)) for b,k,t in re.findall(r'TIME B=(\d+) variant=(\d+) us=([\d.]+)',s) if int(b)==B];assert len(a)==3
  before,candidate,after=[t for k,t in a];out['kernel'].append(dict(policy=name,batch=B,before_us=before,candidate_us=candidate,after_us=after,speedup=(before+after)*.5/candidate))
rows=json.loads((r/'training/results.json').read_text())
for w in ['depth','score']:
 a=[x for x in rows if x['label'].startswith(w) and 'later_seconds' in x]
 if len(a)!=3:continue
 b,c,z=[x['later_seconds'] for x in a];out['training'].append(dict(workload=w,before_seconds=b,candidate_seconds=c,after_seconds=z,steps=a[0]['later_steps'],throughput_gain_percent=((b+z)*.5/c-1)*100,baseline_drift_percent=(z/b-1)*100,mean_game_turns=[x['mean_turn'] for x in a]))
(r/'summary.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
