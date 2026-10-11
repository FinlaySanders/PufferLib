# Local engine benchmark — 2026-09-13

Intel Core i9-14900K. Eight distinct performance cores (logical CPU IDs 0,2,…,14).
GPU unused. Stock NLE 0.9.0 and the installed fast-nle library are called directly from C.
Median of three measured trials after one discarded trial per configuration/workload; alternating engine order.

| Games | Cores | TTY output bound | Workload | Stock keys/s | fast-nle keys/s | Ratio |
|---:|---:|---|---|---:|---:|---:|
| 1 | 1 | no | pri | 393,897 | 182,487 | 0.46× |
| 1 | 1 | no | rog | 349,753 | 187,715 | 0.54× |
| 1 | 1 | no | sam | 383,542 | 138,639 | 0.36× |
| 128 | 1 | no | pri | 48,891 | 180,061 | 3.68× |
| 128 | 1 | no | rog | 51,324 | 186,345 | 3.63× |
| 128 | 1 | no | sam | 54,596 | 192,258 | 3.52× |
| 128 | 4 | no | pri | 199,413 | 743,736 | 3.73× |
| 128 | 4 | no | rog | 212,087 | 767,934 | 3.62× |
| 128 | 4 | no | sam | 230,418 | 772,701 | 3.35× |
| 128 | 8 | no | pri | 455,185 | 1,470,793 | 3.23× |
| 128 | 8 | no | rog | 477,853 | 1,527,905 | 3.20× |
| 128 | 8 | no | sam | 538,596 | 1,552,343 | 2.88× |
| 128 | 1 | yes | pri | 39,869 | 136,118 | 3.41× |
| 128 | 1 | yes | rog | 41,649 | 142,085 | 3.41× |
| 128 | 1 | yes | sam | 43,215 | 147,229 | 3.41× |

## Interpretation

With 128 games, the measured advantage ranges from **2.88× to 3.73×** with terminal arrays unbound. On eight cores, fast-nle delivers **1.47–1.55 million engine keys/s**, versus **0.46–0.54 million** for stock.

**Stock is faster on the single-game tests.** Those step-only measurements last only a few milliseconds and should be treated as exploratory; the longer batched tests are the main result. There is no support here for a universal per-game speedup or a 10× headline.

The parallel setup gives stock one native C worker process per core (no Python or per-step IPC); fast-nle uses one process with one stepping thread per core. Both have 128 total environments, equal core affinity, the same actions, and the same bound observation arrays. Stock isolates environments using private memfd copies of its existing library. fast-nle shares one library with separate game contexts.

This comparison measures the combined installed implementations. It does not separately attribute gains to state layout, algorithm changes, compiler choices or threading. Stock also scales well with additional cores; the result is principally higher batched throughput, not proof of superior parallel scaling efficiency.

The six compared observation channels are glyphs, characters, colours, specials, blstats and messages. They match after every key in the single-environment validation prefixes. Every timing trial also verifies that all environments finish with the same hash, and each stock/fast pair has equal turn advances and final hashes. Inventory and TTY-array equality are not covered by that hash.

## Workload and timing boundaries

- Priest: 1,500 keys, 419 turn advances. Rogue: 968 keys, 245 turn advances. Samurai: 358 keys, 81 turn advances.
- Selected solely for matching observations, before collecting timings. Other corpus trajectories diverged between the installed builds and are listed in `corpus_check.json`; no cause is assigned here.
- These are shallow scripted trajectories, all ending with score zero. Each batch duplicates the same trajectory across environments. This is not representative evidence for deep games, the trained policy, or arbitrary seeds.
- Engine stepping is timed separately from library loading, environment initialization, trace validation and cleanup. There is no policy inference or learner update in these numbers. Initialization timings are also retained in the raw records.
- Clock pinned to epoch 1600000000 and UTC using a separate interposer. Neither stock source nor its engine binary was modified. No ttyrec recording and no partial observation fills.
- Stock baseline build flags are not established here. Binary hashes, CPU details, harness source hash and exact timings are retained. This is an installed-build comparison, not a compiler-controlled optimization ablation.

## Memory and terminal work

- 1 core(s), 128 initialized games: stock **399.0 MiB PSS**, fast-nle **42.6 MiB PSS**, a **9.4×** reduction. PSS was sampled after initialization, before stepping; it is not peak gameplay memory.
- 8 core(s), 128 initialized games: stock **403.0 MiB PSS**, fast-nle **42.6 MiB PSS**, a **9.5×** reduction. PSS was sampled after initialization, before stepping; it is not peak gameplay memory.
- Leaving terminal arrays unbound makes fast-nle **1.31–1.32× faster** here. No partial-fill or direct-export-versus-farlook timing ablation was run.

## Actual training time (separate evidence)

The retained drone launch and completion logs show the two 4B runs took approximately **19 h 6 min** (s705) and **18 h 30 min** (s706), each using one GPU in the eight-RTX-4090 box and a configured 24-thread environment pool. These were concurrent campaign runs, not isolated hardware benchmarks. The last saved checkpoint is 3,999,793,152 policy steps; runs subsequently exited with rc=134 during final evaluation. See `training_evidence.json` and `../certificates/evidence/nh_fixwt.sh`.

These times include the training workload and brief finalization, unlike the engine-only key rates above. They do not establish a stock-versus-fast training speedup.

## Reproduction

```sh
cc -O2 -DSTOCK -I/puffertank/nle-stock/include resources/article/benchmark/engine.c -ldl -lpthread -o resources/article/benchmark/engine_stock
cc -O2 -Ivendor/fast-nle/include -Ivendor/fast-nle/build/_deps/deboost_context-src/include resources/article/benchmark/engine.c -ldl -lpthread -o resources/article/benchmark/engine_fast
cc -O2 -shared -fPIC vendor/fast-nle/tools/faketime_shim.c -o resources/article/benchmark/faketime.so
python3 resources/article/benchmark/check_corpus.py
python3 resources/article/benchmark/run.py
python3 resources/article/benchmark/summarize.py
```

Paths and core IDs reflect this machine. Raw logs and scripts are local article artifacts, not upstream engine changes.
