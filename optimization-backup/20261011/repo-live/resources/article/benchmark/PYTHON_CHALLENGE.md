# Actual Python challenge interface benchmark

Eight distinct i9-14900K performance cores. All arms replay identical actions and request the challenge default observation arrays, including inventory and terminal output.

| Games | Stock NLE (C) keys/s | Python NetHackChallenge-v0 steps/s | fast-nle (C) keys/s | fast-nle / Python |
|---:|---:|---:|---:|---:|
| 8 | 1,353,340 | 578,889 | 886,586 | 1.53× |
| 128 | 341,371 | 223,300 | 1,004,138 | 4.50× |
| 512 | 109,642 | 89,554 | 720,553 | 8.05× |
| 1024 | 102,517 | 87,213 | 467,916 | 5.37× |

## What was actually called

The Python arm uses installed Gym 0.23.0 and stock NLE 0.9.0 via `gym.make("NetHackChallenge-v0")`, `reset()` and `step()`. It includes the actual challenge wrapper and its copies, reward computation and termination accounting. It does not use the project's stock reconstruction adapter or neural-network policy. Action indices are prepared before timing.

For reproducibility only, this diagnostic sets a fixed character and options matching the recorded workloads, and sets initial seeds through the native object before reset. The challenge normally disables seeding. This is therefore **a timing diagnostic using the actual challenge wrapper, not an unseeded challenge certificate or submission**. No NLE source or library files are changed; these settings are local to each benchmark process. The clock is pinned externally to epoch 1600000000 UTC, recording is disabled, and reset/menu startup is excluded from timing.

Stock C also binds the challenge observation fields and internal bookkeeping arrays, and performs the same startup-space handling before timing. fast-nle C does likewise. No partial observation fills or extra engine exports are used. This is a fuller observation workload than the original C microbenchmark, so compare numbers within this table rather than mixing tables.

Both stock arms have eight processes with an equal share of environments; fast-nle uses eight threads in one process. Workers are pinned to eight distinct performance cores. Python executes the per-step loop inside each worker with no per-step interprocess traffic. Library loading, environment initialization, final hashing and cleanup are excluded.

## Validation and aggregation

Three early-game sequences: Priest 1,500 keys/419 turn advances, Rogue 968/245, Samurai 358/81. All 14 public observation arrays match byte-for-byte hashes after every key in the single-environment validation across all three arms. Each timed trial checks final hashes across its environments; all measured three-arm groups agree on final hashes and turn advances. No terminal episode occurs inside these prefixes, so the timing does not cover death/reset handling.

Each configuration/workload has one discarded first trial plus three measured trials, with rotating backend order. Table rates divide total keys across all three workloads by the sum of median step times. The small 8-game timings are more sensitive to scheduling noise. Raw measurements are in `challenge_timings.jsonl`, source/binary identifiers in `challenge_machine.json`, and prefix checks in `challenge_validation.json`.

These are repeated copies of shallow, zero-score scripted trajectories, not a distribution of trained-agent games. Ratios do not establish full training speedup, deep-game speedup, or the gain from replacing farlook probes with direct exports. This run measures stepping through Python's challenge interface versus native engine stepping with matched observations.

## Initialized memory

| Games | Stock C PSS | Python PSS | fast-nle C PSS |
|---:|---:|---:|---:|
| 8 | 28.6 MiB | 258.9 MiB | 6.1 MiB |
| 128 | 403.9 MiB | 639.6 MiB | 49.4 MiB |
| 512 | 1604.2 MiB | 1859.5 MiB | 187.7 MiB |
| 1024 | 3207.7 MiB | 3485.8 MiB | 372.2 MiB |

PSS is summed across workers immediately after initialization. It is not peak gameplay memory.

## Reproduce

From the repository root, with the existing local NLE installation:

```sh
cc -O2 -DSTOCK -I/puffertank/nle-stock/include resources/article/benchmark/engine_challenge.c -ldl -lpthread -o resources/article/benchmark/challenge_stock_c
cc -O2 -Ivendor/fast-nle/include -Ivendor/fast-nle/build/_deps/deboost_context-src/include resources/article/benchmark/engine_challenge.c -ldl -lpthread -o resources/article/benchmark/challenge_fast_c
python3 resources/article/benchmark/check_challenge.py
python3 resources/article/benchmark/run_challenge.py
python3 resources/article/benchmark/summarize_challenge.py
```

Uses `faketime.so` built by the original benchmark instructions. No scored evaluation or training jobs are started.

## Fairness clarification

See [the fairness audit](FAIRNESS.md). The native arm is the engine, not the complete PufferLib environment. The Python/C difference includes wrapper work, not just Python execution cost. Ratios must not be presented as end-to-end training speedups.
