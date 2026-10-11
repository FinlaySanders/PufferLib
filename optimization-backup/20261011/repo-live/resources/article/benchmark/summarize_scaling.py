import json,statistics as st,csv
from run import B,CASES
raw=[json.loads(l) for l in (B/'scaling_games.jsonl').read_text().splitlines()]
assert len(raw)==json.loads((B/'scaling_complete.json').read_text())['trials']==120
rows=[]
for n in (8,32,128,512,1024):
 d={'games':n,'cores':8};ratios=[]
 for engine in ('stock','fast'):
  selected=[r for r in raw if r['envs']==n and r['engine']==engine and r['rep']>0]
  assert len(selected)==9
  seconds=0;calls=0
  for case,keys in CASES:
   trials=[r for r in selected if r['case']==case]
   seconds+=st.median(r['seconds'] for r in trials);calls+=n*keys
  d[engine+'_keys_per_second']=calls/seconds
  d[engine+'_initial_pss_mib']=st.median(r['pss_kib'] for r in selected)/1024
 for case,keys in CASES:
  speed={engine:st.median(r['sps'] for r in raw if r['envs']==n and r['engine']==engine and r['case']==case and r['rep']>0) for engine in ('stock','fast')}
  ratios.append(speed['fast']/speed['stock'])
 d['ratio']=d['fast_keys_per_second']/d['stock_keys_per_second']
 d['ratio_min_workload']=min(ratios);d['ratio_max_workload']=max(ratios);rows.append(d)
with (B/'scaling_summary.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
lines=['# Scaling with concurrent games','','Eight distinct i9-14900K performance cores, fixed throughout. Stock: eight native worker processes. fast-nle: eight threads in one process. Same three early-game workloads as [the initial benchmark](RESULTS.md). No Python calls, policy inference or learning in either arm.','','| Games | Stock keys/s | fast-nle keys/s | Ratio | Stock initial PSS | fast-nle initial PSS |','|---:|---:|---:|---:|---:|---:|']
for d in rows:
 lines.append(f"| {d['games']} | {d['stock_keys_per_second']:,.0f} | {d['fast_keys_per_second']:,.0f} | {d['ratio']:.2f}× | {d['stock_initial_pss_mib']:.1f} MiB | {d['fast_initial_pss_mib']:.1f} MiB |")
lines+=['','Rates = total keys across the three workloads divided by the sum of their median step times. Each median uses three trials after a discarded first trial; engine order alternates. This weights by the recorded workloads rather than averaging rates. Per-workload ratio ranges are in `scaling_summary.csv`.','','All 60 stock/fast pairs have matching final hashes and turn advances. Each trial also checks that every environment finishes with the same hash. The initial single-game validation compared six observation channels after every key in these prefixes; this is not proof of complete game-state equality.','','The 8-game timings are short and relatively sensitive to scheduling overhead. Memory is proportional set size after initialization, not peak gameplay usage. Batches repeat the same seed and actions: these are controlled early-game microbenchmarks, not diverse trained-policy games. No conclusion about deep-game or end-to-end training speed follows directly.','','Reproduce from the repository root:','','```sh','python3 resources/article/benchmark/scale_games.py','python3 resources/article/benchmark/summarize_scaling.py','```']
(B/'SCALING.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines[:13]))
