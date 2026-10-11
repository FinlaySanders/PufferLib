import json,statistics as st,csv,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent
raw=[json.loads(l) for l in (B/'timings.jsonl').read_text().splitlines()]
assert json.loads((B/'complete.json').read_text())['trials']==len(raw)==120
rows=[r for r in raw if r['rep']>0]
summary=[]
for tty,workers,envs in [(0,1,1),(0,1,128),(0,4,128),(0,8,128),(1,1,128)]:
 for case in sorted({r['case'] for r in rows}):
  d=dict(tty=tty,cores=workers,envs=envs,case=case)
  for kind in ('stock','fast'):
   v=[r for r in rows if (r['tty'],r['workers'],r['envs'],r['case'],r['engine'])==(tty,workers,envs,case,kind)]
   assert len(v)==3
   for field in ('sps','pss_kib','seconds','init_seconds'):
    d[kind+'_'+field]=st.median(r[field] for r in v)
   d[kind+'_sps_min']=min(r['sps'] for r in v);d[kind+'_sps_max']=max(r['sps'] for r in v)
  d['speedup']=d['fast_sps']/d['stock_sps'];summary.append(d)
with (B/'summary.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
lines=['# Local engine benchmark — 2026-09-13','','Intel Core i9-14900K. Eight distinct performance cores (logical CPU IDs 0,2,…,14).',
       'GPU unused. Stock NLE 0.9.0 and the installed fast-nle library are called directly from C.',
       'Median of three measured trials after one discarded trial per configuration/workload; alternating engine order.', '',
       '| Games | Cores | TTY output bound | Workload | Stock keys/s | fast-nle keys/s | Ratio |',
       '|---:|---:|---|---|---:|---:|---:|']
for d in summary:
 lines.append(f"| {d['envs']} | {d['cores']} | {'yes' if d['tty'] else 'no'} | {d['case'].split('_')[0]} | {d['stock_sps']:,.0f} | {d['fast_sps']:,.0f} | {d['speedup']:.2f}× |")
lines += ['', '## Interpretation', '',
 'With 128 games, the measured advantage ranges from **2.88× to 3.73×** with terminal arrays unbound. On eight cores, fast-nle delivers **1.47–1.55 million engine keys/s**, versus **0.46–0.54 million** for stock.', '',
 '**Stock is faster on the single-game tests.** Those step-only measurements last only a few milliseconds and should be treated as exploratory; the longer batched tests are the main result. There is no support here for a universal per-game speedup or a 10× headline.', '',
 'The parallel setup gives stock one native C worker process per core (no Python or per-step IPC); fast-nle uses one process with one stepping thread per core. Both have 128 total environments, equal core affinity, the same actions, and the same bound observation arrays. Stock isolates environments using private memfd copies of its existing library. fast-nle shares one library with separate game contexts.', '',
 'This comparison measures the combined installed implementations. It does not separately attribute gains to state layout, algorithm changes, compiler choices or threading. Stock also scales well with additional cores; the result is principally higher batched throughput, not proof of superior parallel scaling efficiency.', '',
 'The six compared observation channels are glyphs, characters, colours, specials, blstats and messages. They match after every key in the single-environment validation prefixes. Every timing trial also verifies that all environments finish with the same hash, and each stock/fast pair has equal turn advances and final hashes. Inventory and TTY-array equality are not covered by that hash.', '',
 '## Workload and timing boundaries', '',
 '- Priest: 1,500 keys, 419 turn advances. Rogue: 968 keys, 245 turn advances. Samurai: 358 keys, 81 turn advances.',
 '- Selected solely for matching observations, before collecting timings. Other corpus trajectories diverged between the installed builds and are listed in `corpus_check.json`; no cause is assigned here.',
 '- These are shallow scripted trajectories, all ending with score zero. Each batch duplicates the same trajectory across environments. This is not representative evidence for deep games, the trained policy, or arbitrary seeds.',
 '- Engine stepping is timed separately from library loading, environment initialization, trace validation and cleanup. There is no policy inference or learner update in these numbers. Initialization timings are also retained in the raw records.',
 '- Clock pinned to epoch 1600000000 and UTC using a separate interposer. Neither stock source nor its engine binary was modified. No ttyrec recording and no partial observation fills.',
 '- Stock baseline build flags are not established here. Binary hashes, CPU details, harness source hash and exact timings are retained. This is an installed-build comparison, not a compiler-controlled optimization ablation.', '',
 '## Memory and terminal work', '']
for workers in (1,8):
 ds=[d for d in summary if (d['tty'],d['envs'],d['cores'])==(0,128,workers)]
 sm=st.median(d['stock_pss_kib'] for d in ds)/1024;fm=st.median(d['fast_pss_kib'] for d in ds)/1024
 lines.append(f'- {workers} core(s), 128 initialized games: stock **{sm:.1f} MiB PSS**, fast-nle **{fm:.1f} MiB PSS**, a **{sm/fm:.1f}×** reduction. PSS was sampled after initialization, before stepping; it is not peak gameplay memory.')
ratios=[]
for d in summary:
 if (d['tty'],d['envs'],d['cores'])==(0,128,1):
  other=next(o for o in summary if (o['tty'],o['envs'],o['cores'],o['case'])==(1,128,1,d['case']))
  ratios.append(d['fast_sps']/other['fast_sps'])
lines += [f'- Leaving terminal arrays unbound makes fast-nle **{min(ratios):.2f}–{max(ratios):.2f}× faster** here. No partial-fill or direct-export-versus-farlook timing ablation was run.', '',
 '## Actual training time (separate evidence)', '',
 'The retained drone launch and completion logs show the two 4B runs took approximately **19 h 6 min** (s705) and **18 h 30 min** (s706), each using one GPU in the eight-RTX-4090 box and a configured 24-thread environment pool. These were concurrent campaign runs, not isolated hardware benchmarks. The last saved checkpoint is 3,999,793,152 policy steps; runs subsequently exited with rc=134 during final evaluation. See `training_evidence.json` and `../certificates/evidence/nh_fixwt.sh`.', '',
 'These times include the training workload and brief finalization, unlike the engine-only key rates above. They do not establish a stock-versus-fast training speedup.', '',
 '## Reproduction', '', '```sh',
 'cc -O2 -DSTOCK -I/puffertank/nle-stock/include resources/article/benchmark/engine.c -ldl -lpthread -o resources/article/benchmark/engine_stock',
 'cc -O2 -Ivendor/fast-nle/include -Ivendor/fast-nle/build/_deps/deboost_context-src/include resources/article/benchmark/engine.c -ldl -lpthread -o resources/article/benchmark/engine_fast',
 'cc -O2 -shared -fPIC vendor/fast-nle/tools/faketime_shim.c -o resources/article/benchmark/faketime.so',
 'python3 resources/article/benchmark/check_corpus.py',
 'python3 resources/article/benchmark/run.py',
 'python3 resources/article/benchmark/summarize.py', '```', '',
 'Paths and core IDs reflect this machine. Raw logs and scripts are local article artifacts, not upstream engine changes.']
(B/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines[26:34]))
