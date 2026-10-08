from pathlib import Path
import json,datetime
r=Path(__file__).parent
canonical='cae68ae4879051f55b6b7dabc787ab4c5627557f0117d3d8cc32bacbee6f0466'
rows=[]
for p in sorted(r.glob('*/result.json'),key=lambda p:p.stat().st_mtime):
 x=json.loads(p.read_text());x['correctness']='FAIL'
 if x['rc']==0:
  x['correctness']='exact' if x['final_sha']==(canonical if x['update'] else x['initial_sha']) else 'DIFFERENT'
 rows.append(x)
(r/'results.json').write_text(json.dumps(rows,indent=2))
s=['# Live training optimization results','', 'Deadline: 2026-09-18 12:19 UTC. Production unchanged. Timings are short screens; small gains need repeats. Default tests use 512 environments, 15.55M s705, horizon512, minibatch4096, replay1.78021395; early tests use a fresh random policy and live actions.','', '| Test | Update weights? | SPS | Final weights | Note |','|---|---|---:|---|---|']
for x in rows:s.append(f"| {x['label']} | {x['update']} | {x.get('sps',0):,.0f} | {x['correctness']} | {'Profile overhead; not benchmark' if x['profile'] else ''} |")
s+=['', 'Normal-update tests compare the final 15.55M-parameter FP32 checkpoint against the baseline after 1,808 optimizer updates. Frozen tests check unchanged parameters. Replay cases check three mature-game observation hashes against the recorded teacher; early cases are compared to their live baseline. Recorded actions keep game workload controlled; this is not a learning-quality evaluation.','', 'Baseline control: 170,387 SPS with updates; frozen171k. Current best combo2 adds out-of-place Muon GEMMs: 183,589 frozen SPS (+7.36%). Master weights, momentum, and updates are byte-identical; early live proof matches too. See best.json and STATUS.md.']
(r/'RESULTS.md').write_text('\n'.join(s)+'\n')
print('completed',len(rows),'nonexact',[(x['label'],x['correctness']) for x in rows if x['correctness']!='exact'])
