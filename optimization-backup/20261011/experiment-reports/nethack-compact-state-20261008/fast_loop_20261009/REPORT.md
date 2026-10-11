# Fast NetHack optimisation loop — 9 October 2026

## Decision

Use fast recorded-action warm-up, then restart short ordinary-rollout trials from a quiescent CPU process snapshot that also restores private game files and seekable descriptor offsets. Keep the engine binary fixed within a snapshot. Rebuild and prepare a new snapshot for every changed engine binary; never load a different engine into an existing snapshot.

The measured default is **2048 environments × 512 decisions** for the first screen, followed by **512 environments × 2048 decisions** for candidates worth pursuing. These each execute 1,048,576 ordinary decisions. Confirm close/promising results with the full 2048 × 2048 window. No burst scheduling in measured windows.

## Warm-up experiment

All runs warm to decision 8192. Fast warm-up uses chunks of recorded actions, then ordinary stepping for at least 128 decisions before timing. Endpoint observations, game ages and world-turn counts match the unchanged baseline.

| Warm chunk | Warm-up seconds at 2048 | Measured ordinary SPS |
|---:|---:|---:|
| 1 | 71.48 | 216201 |
| 128 | 39.78 | 216475 |
| 512 | 40.69 | 216505 |

Choose 128: 512 is not faster. This saves about 32 seconds of preparation. It is a benchmark setup optimisation, not a production rollout speedup.

## Timing reliability

Control A and the previously tested ready-buffer recheck B run in A–B–B–A order. A snapshot includes the same mature state and recorded action window for every child. Each child recreates workers and performs 128 ordinary untimed decisions before measuring. All timing tests are native; proof and profile runs are separate. 24 pinned workers, four pinned submitters, unchanged machine settings, serialized heavy work.

| Games | Decisions/game | Control SPS | Candidate SPS | Difference | Control repeat range | Four trials after prep |
|---:|---:|---:|---:|---:|---:|---:|
| 512 | 2048 | 294,484 | 282,672 | -4.01% | 0.14% | 16.1s |
| 2048 | 512 | 214,882 | 235,811 | +9.74% | 0.07% | 26.0s |
| 2048 | 2048 | 216,389 | 236,784 | +9.43% | 0.15% | 81.3s |

The short 2048 window finds +9.74%, versus +9.43% on the longer window and +9.54% in the previous independent long study. At 512 it reproduces the known approximately 4% regression. This validates rejection/prioritisation of a clear effect, not sensitivity to every sub-percent change. The two-repeat ranges are descriptive, not confidence intervals.

Preparation is 9.9s for 512 and 39.0s for 2048, once per snapshot/binary. Four restored trials then cost 16.1s and 26.0s respectively, including file restoration, ordinary settling, measurement and child cleanup. A fresh 2048 short four-trial batch costs about 65 seconds. Testing both sizes for a runtime variant in this binary is about 90 seconds including both preparations. Arbitrary source candidates need their own preparation; do not quote post-preparation timing as total build-to-result time.

## Profiling

The short ordinary 2048 window takes 4.89s with sampling enabled (6.36s including child startup/settling/cleanup, plus file restoration). See profile.txt. Profile timing is excluded from native comparisons. Reuse a prepared snapshot for this diagnostic alongside native trials.

It collected 5,367 samples. Monster-turn processing is 61.9% inclusive versus 62.6% in the previous long profile; movement and neighbour checks together are 38.2% self versus 38.4%. The short profile selects the same major targets. It does not resolve tiny costs with comparable precision.

## Correctness and the failed first attempt

The first memory-only fork test was rejected: its first child matched, but subsequent children diverged. NetHack's temporary level files survive outside process memory, child cleanup deletes those directories, and inherited seekable file descriptors share offsets. The repaired helper restores the private vardir and its file contents before each fork, then restores descriptor offsets. All pool/OpenMP workers are stopped and /proc/self/task must show exactly one thread before snapshotting. Both execution paths use the unchanged retained engine.

Across 512 and 2048 cases, **6,291,456 per-decision hashes match the pre-existing immutable reference, with 0 differences**. Hashes cover observations, rewards, terminal flags and action masks. Short and long native endpoints also match. Scope is the tested bounded trajectories, not a proof of all possible game states. Full golden/fuzz/trajectory gates remain mandatory before retaining new engine changes.

Reference: /puffertank/experiments/nethack-cpu-scaling-20261008/runs/final_hash_opt61/hashes.bin

SHA256: 4d35f6965a68e81b13d55f6032ed39b09839cd3525ede0c71a12918f7bc9d047

Retained engine: /puffertank/experiments/nethack-compact-state-20261008/engines/monmove_guard_pgo/build/libnethack.so

SHA256: 2a5cfac52f27a7430383c00e0c2a84ae96cdc12c64c2decbb993aeea8ec2ce84

## Loop to use

1. Profile a short prepared ordinary window only when it will select the next hypothesis. Do not reprofile for every small edit.
2. Implement one isolated candidate and run quick correctness gates. Compile fast for screening; do expensive PGO builds only for promising source candidates, comparing like-for-like builds.
3. Prepare its mature state once using warm chunks of 128. Screen at 2048 × 512; keep baseline/candidate actions, worker settings and measured windows identical. A cached control can prioritize a candidate but cannot establish a win.
4. For a plausible win, collect fresh A–B–B–A comparisons, check 512 as well, and require a gain larger than observed control drift. Clear several-percent results can move on quickly. Borderline results need a longer window/more repeats; park changes that remain within noise.
5. Run separate per-decision proofs, full golden/fuzz and score/depth corpus gates before retention. Run the mature frozen-policy training pipeline only for confirmed CPU winners. CPU gains may remain hidden behind GPU work.

The supplied runner accepts a list of trials per snapshot. For general source changes, use focus 0 with --engine pointing to that candidate build directory; prepare a separate snapshot for the control build. Focus 1 exists only to reproduce this known scheduler test. Focus 2 profiles control.

## Commands

```bash
# Existing retained engine: short controls plus a short profile, one preparation.
python /puffertank/experiments/nethack-compact-state-20261008/fast_loop_20261009/snapshot_test.py my_profile 2048 '0:512,0:512,2:512'

# Candidate engine: two short native trials from the same restored state.
python /puffertank/experiments/nethack-compact-state-20261008/fast_loop_20261009/snapshot_test.py my_candidate 2048 '0:512,0:512' --engine /absolute/path/to/candidate/build

# Exact per-decision check of that candidate; excluded from native timing.
python /puffertank/experiments/nethack-compact-state-20261008/fast_loop_20261009/snapshot_test.py my_candidate_proof 2048 '0:512,0:512' --engine /absolute/path/to/candidate/build --proof
```

Labels must be unique so results are never overwritten. This harness is CPU-only; do not apply fork snapshots to an initialized CUDA training process. No production code, retained source/library, training defaults, or reference expectations changed. No commit or push. Commands, source, raw results and the rejected experiment are retained in this directory.

The current runner takes a fixed batch of trial requests and exits after completing them; it is not a resident benchmark service. The one-binary A–B–B–A test above compares runtime scheduler flags. Fresh compiled engines require separate snapshots and a fresh paired confirmation. Snapshot timings also incur copy-on-write faults; they agree with fresh-process timing in this test, but memory-layout candidates should still be confirmed in a fresh ordinary replay before retention.
