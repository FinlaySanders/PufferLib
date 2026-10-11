# Work status — 26 September 2026

Snapshot of the code and experiments at the time of writing. Remote branches were not fetched for this review, so this is not a fresh upstream-sync check.

## Main checkout

- Location: `/puffertank/pufferlib`
- Branch: `drone-nominal-actions`
- HEAD: `3719caaa` — `small cleanup`
- Previous commit: `1cb95a8a` — `cublas fix`
- Base before those commits: `6ffa5b10` — merge of the NetHack Challenge changes.
- Four tracked files have uncommitted changes, totalling 43 insertions and 42 deletions.
- No GPU jobs were running when checked.

| Modified file | Change |
|---|---|
| `ocean/drone/dronelib.h` | Nominal hover/minimum RPM helpers; reset motor RPM uses nominal parameters. |
| `ocean/drone/physics.h` | Fixed nominal action-to-RPM mapping, independent of randomised physics parameters. |
| `ocean/drone/render.h` | Rotor visualisation matches the nominal action mapping. |
| `ocean/nethack/depth.ini` | Replaces the older depth recipe with the archived stronger recipe and a 2B-step budget. |

No new commit or push was made during this status review.

## Workstreams

| Work | Where it stands | Result |
|---|---|---|
| cuBLAS workspace fix | Committed in this checkout; user opened the PR. | Restored repeatability for affected NetHack/Craftax configurations. Large throughput gain for long-horizon NetHack; little change elsewhere. |
| Drone action centering | Uncommitted changes in three drone headers. | Removes implicit compensation for each randomised drone's physical parameters. Five-seed retraining showed comparable overall performance. |
| NetHack depth config | Uncommitted change to `ocean/nethack/depth.ini`. | Fresh 2B retrain and 10,000-game retained certificate completed. |
| Drone thrust-to-weight probes | Separate experiment; no production changes. | Hidden state contains decodable physical information, but causal use of an explicit parameter estimate is not established. |
| Separate termination/truncation handling | Separate experimental trainer; not applied to this checkout. | Twelve training runs completed. Small overall improvements, with mixed task results. |
| NetHack engine/training optimisations | Preserved in isolated experiment trees and patches. | Additional engine, worker-pool and GPU experiments are not folded into this checkout. |
| NetHack identification/discovery work | Parked research in stashes and experiment directories. | Identify targeting, discovery-encoding changes and probes are not enabled in this checkout. |
| Article, policies and recording tools | Mostly untracked local artifacts. | Figures, certificates, checkpoints, scripts and videos remain available. |

## cuBLAS fix

The committed fix gives concurrent streams their own cuBLAS handles and explicit workspaces. It avoids stream changes resetting the workspace and avoids dependence on cuBLAS's internal scratch allocation availability during graph capture.

Validation covered repeatability, matching upstream where upstream was repeatable, and performance across multiple environments. Long-horizon NetHack improved by about 54% in the tested configuration; most other environments were approximately unchanged. Some unrelated environments remained nondeterministic in both versions.

References:

- `/puffertank/experiments/cublas-all-env-perf-20260918/REPORT.md`
- `/puffertank/experiments/cublas-pool-rule-20260918/REPORT.md`
- `/puffertank/experiments/cublas-final-check-20260918/REPORT.md`

## Drone nominal action mapping

Previously, action centering and initial motor RPM used each drone's true randomised mass, thrust coefficient and gravity. This implicitly supplied a hover calibration. The uncommitted fix uses nominal parameters for both, while keeping the randomised physics.

Five training seeds, each with 89,128,960 steps, were compared on the fixed nominal mapping:

| Metric | Old mapping during training | Nominal mapping during training |
|---|---:|---:|
| Overall performance | 0.8508 | 0.8462 |
| Mean hover distance | 2.80 cm | 2.38 cm |
| Mean hover speed | 0.0586 m/s | 0.0716 m/s |
| Race completion | 98.70% | 98.96% |

This removed implicit calibration without a material overall performance loss. It was not an improvement in every metric, and no new hardware test was performed.

Results: `/puffertank/experiments/drone-nominal-actions-20260924/SEEDS.md`.

## NetHack depth config and retrain

The updated config matches the archived stronger depth recipe used for the previous 2B runs and subsequent 4B retrain. SEARCH20 and RUN remain masked; challenge multi-role remains enabled.

The new seed-906 run completed approximately 2B steps in 2h15m, averaging about 247k steps/s. Its certificate discards the first 4,000 completed games and retains the next 10,000:

| Metric | Result |
|---|---:|
| Mean BALROG progression | 15.90% |
| Maximum BALROG progression | 64.65% |
| Mean maximum depth | 10.7082 |
| Maximum depth | 29 |

The BALROG progression calculation takes the higher of the depth and XP-level lookup values. It is not the complete BALROG evaluation protocol. The maximum corresponds to depth 29; these logs do not establish an actual Castle visit.

- Certificate, including per-role results: `/puffertank/experiments/depth-nominal-config-20260924/cert/RESULTS.md`
- Checkpoint: `/puffertank/experiments/depth-nominal-config-20260924/checkpoints/nethack/depth2b_s906/0000001999962112.bin`

## Drone thrust-to-weight probes

Three policy seeds were tested at each of 5%, 15% and 30% domain randomisation. The target was maximum available thrust divided by weight:

```text
4 × thrust_coefficient × max_RPM² / (mass × gravity)
```

Each evaluation collected 4,096 fresh episodes, balanced between hover and racing. Readouts used held-out episodes and frozen CPU policy inference.

Nonlinear hidden-state decoding after five seconds, at each policy's training distribution:

| Randomisation | Hover R² | Racing R² |
|---|---:|---:|
| 5% | 0.977 | 0.082 |
| 15% | 0.984 | 0.292 |
| 30% | 0.985 | 0.642 |

Wider randomisation also makes the physical differences easier to observe. On the same 30% test distribution, racing hidden-state decoding was similar for the 5%-trained and 30%-trained policies: 0.650 versus 0.642. For the 30%-trained policy, current observations achieved only 0.310, showing a substantial readout advantage from recurrent state.

On that common test, mean hover distance after five seconds fell from 9.76 cm with 5% training DR to 5.63 cm with 30% training DR. During hover, observations alone already decode thrust-to-weight very well. These findings do not prove that the policy maintains and causally uses an explicit estimate.

Results and methods: `/puffertank/experiments/drone-twr-probe-20260924/RESULTS.md` and `METHODS.md`.

## Separate termination and truncation experiment

The main trainer still uses one terminal/boundary flag for GAE. Drone time limits and spatial failures both set it, suppressing value bootstrapping.

The isolated prototype records timeout-only flags and final observations before reset. At a timeout it evaluates the final observation using the old episode's recurrent state, then adds `gamma × final_value` to the reward used by GAE. The boundary flag still stops the advantage trace and resets recurrent state. True failures receive no bootstrap; failure takes precedence if simultaneous with a timeout.

This is algebraically equivalent to separate terminal/truncation handling. The GAE kernel itself is unchanged. The prototype is restricted to the single-policy CPU drone environment and performs an extra batched forward each step; it is not an upstream-ready general implementation.

Three paired seeds per setting, approximately 89M training steps each, with 4,096 evaluation episodes per policy using the same unmodified evaluator:

| DR | Handling | Overall performance ↑ | Hover distance ↓ | Hover speed | Race completion ↑ |
|---|---|---:|---:|---:|---:|
| 5% | Single done | 0.847 | 2.47 cm | 0.071 m/s | 99.23% |
| 5% | Separate truncation | 0.851 | 2.40 cm | 0.066 m/s | 99.20% |
| 30% | Single done | 0.752 | 6.97 cm | 0.159 m/s | 81.43% |
| 30% | Separate truncation | 0.759 | 6.10 cm | 0.163 m/s | 79.97% |

The change helped hover modestly but did not improve every metric. Three seeds do not establish a reliable general gain.

Validation passed for CUDA GAE equations, final observations, failure precedence and reset flags. Original/off/on short training runs produced byte-identical checkpoints before any timeout. All final checkpoints were finite.

Artifacts: `/puffertank/experiments/drone-truncation-20260925/`, including `RESULTS.md`, `METHODS.md`, `experiment.patch`, source, logs and checkpoints.

## Parked NetHack research and local artifacts

- Engine and shared-worker-pool optimisation work: `/puffertank/experiments/nethack-overnight-20260917/`.
- Additional training/GPU optimisation work: `/puffertank/experiments/nethack-train-loop-20260918/`.
- Identification training: `/puffertank/experiments/identify-training-20260915/`.
- Discovery replacement and probes: `/puffertank/experiments/identify-replacement-20260916/`, `/puffertank/experiments/discovery-probes-20260916/`, and `/puffertank/experiments/discovery-supervised-20260916/`.
- Current `stash@{0}`: `nethack work before reviewing cublas`.
- Current `stash@{1}`: NetHack find/watch and action-recording tooling. Stash indices can change; use the descriptions to identify them later.
- Untracked artifacts include `resources/article/`, policy files in `resources/nethack/`, `scripts/`, `nethack_videos/`, recordings, probe tests and local binaries. These are not all intended for upstream.

The nested `vendor/fast-nle` repository is at `e7f656856` (`nethack challenge`). Its tracked source is clean; `build-web/` is untracked. Additional experimental engine optimisations are not applied there.

## Suggested next cleanup

Prepare two separate commits when requested:

1. Drone nominal action mapping and matching rendering.
2. Updated NetHack depth config.

Keep the truncation prototype, probes and other research separate until deciding which changes to promote. Do not push branches or open PRs automatically; the user handles publication.
