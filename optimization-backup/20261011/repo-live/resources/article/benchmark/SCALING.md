# Scaling with concurrent games

Eight distinct i9-14900K performance cores, fixed throughout. Stock: eight native worker processes. fast-nle: eight threads in one process. Same three early-game workloads as [the initial benchmark](RESULTS.md). No Python calls, policy inference or learning in either arm.

| Games | Stock keys/s | fast-nle keys/s | Ratio | Stock initial PSS | fast-nle initial PSS |
|---:|---:|---:|---:|---:|---:|
| 8 | 2,167,052 | 1,120,956 | 0.52× | 28.5 MiB | 5.6 MiB |
| 32 | 2,128,742 | 1,476,031 | 0.69× | 103.2 MiB | 13.0 MiB |
| 128 | 473,008 | 1,465,387 | 3.10× | 403.3 MiB | 42.6 MiB |
| 512 | 139,600 | 1,196,909 | 8.57× | 1601.3 MiB | 160.9 MiB |
| 1024 | 120,150 | 731,317 | 6.09× | 3207.9 MiB | 318.6 MiB |

Rates = total keys across the three workloads divided by the sum of their median step times. Each median uses three trials after a discarded first trial; engine order alternates. This weights by the recorded workloads rather than averaging rates. Per-workload ratio ranges are in `scaling_summary.csv`.

All 60 stock/fast pairs have matching final hashes and turn advances. Each trial also checks that every environment finishes with the same hash. The initial single-game validation compared six observation channels after every key in these prefixes; this is not proof of complete game-state equality.

The 8-game timings are short and relatively sensitive to scheduling overhead. Memory is proportional set size after initialization, not peak gameplay usage. Batches repeat the same seed and actions: these are controlled early-game microbenchmarks, not diverse trained-policy games. No conclusion about deep-game or end-to-end training speed follows directly.

Reproduce from the repository root:

```sh
python3 resources/article/benchmark/scale_games.py
python3 resources/article/benchmark/summarize_scaling.py
```
