# NetHack optimisation backup — 8 October 2026

Branch: `backup/nethack-optimizations-20261008`.
Base: `3719caaaf945025e4e1e59c6556560d2ba9e3d1c` (includes the cuBLAS fix).
Companion: the same branch in `FinlaySanders/fast-nle`.

The unmerged work is preserved under `optimization-backup/20261008/` as exact
source overlays, patches, build recipes and validation reports. The normal
trainer source at the repository root has not been replaced by a historical
experimental trainer. The live checkout and running experiments were untouched.

## What is saved

- `training/minimal/`: the retained implementation without optional validation
  instrumentation; `training/retained/` preserves the instrumented version.
- `training/baseline/`: the exact source overlay against which
  `training/optimizations-only.patch` was produced. It already contains the
  engine-pool, sampler and cuBLAS work. The patch is not relative to upstream.
- `scheduler/retained/` and `scheduler/shared-pool83.patch`: the original shared
  worker pool, with source manifests and concurrency/rollout validation reports.
- `sampler/`: score and identify-capable variants of the head-parallel sampler,
  their source overlays, portable patches, test scripts and reports.
- `initial-campaign/`: the earlier work-stealing patches and combined engine/
  scheduler measurements.
- `gemm/`: the earlier GPU optimisation report, scripts and saved patch.
- `parked/`: source changes from the pre-cuBLAS NetHack stash, with its original
  commit and base. This also includes identification research; it is not a
  performance-only patch. Its compiled executable is omitted.

The later training changes are batched Muon normalization, separate-output
Newton–Schulz GEMMs, removal of redundant MinGRU copies, skipping unused-head
log-probability work, coalesced gradient zeroing, raw-byte observation storage,
and rollout-graph reuse. They remain optional historical implementations with
their original build flags and configuration.

## Recovery and validation

The overlays contain `src/`, `ocean/nethack/`, `config/` and `build.sh`. They
preserve historical code exactly, including benchmark hooks and alternative
implementations. Use them in an isolated checkout with the companion fast-nle
source when reviewing or reintegrating the changes. `training/build_minimal.sh`
records the retained flags. External dependencies, policy weights and recorded
trajectories are not included; archived benchmark scripts retain original
absolute paths.

The historical reports contain checkpoint, optimizer-state, trajectory and
kernel equivalence results and their limits. Backup verification checks source
hashes and patch reconstruction; it does not claim a new training or performance
test. Saved candidate scripts include rejected experiments: use `training/best.json`
and `scheduler/best.json` to identify the retained variants.

`optimization-backup/20261008/MANIFEST.json` records the original path, size and
SHA-256 of each copied file. This branch preserves optimisation code and compact
supporting evidence, not the large data/checkpoint backup discussed earlier.

## Addendum — 11 October 2026 (`optimization-backup/20261011/`)
- `trainer-cohort/`: `trainer_cohort_ini_keys.patch` ([vec] cohort_buffers / cohort_steps, validated: rollout proofs identical, +26% at 5M/2048),
  `trainer_cohort_knobs.patch` (same plus two refuted probes), and `overlay/` = the full experiment trainer as last built (env pool, cohort knobs,
  generalised pinning, per-worker stats, 64-agent replay relaxation).
- `engine-scaling/`: PROGRAM.md (chronological ledger), HANDOFF.md (close-outs), designs, footprint/branch/function censuses, every chain script,
  layer generators, the cohort harness (harness_cohort/replay_cohort.c) and the engine patches (engine_mt7stack_*, engine_dv4stack_*).
- `harness-24h/`: the frozen-policy trainer harness (run_scale.py with --extra/--source/--buffers 32/64, campaign_ablate.py, every ablate_*.json
  spec and results, pool_timing_report.py, thread_util.sh, sps_from_log.py) and `source-src/` = the 24h experiment trainer's src/ as run.
Recommended config for collection-bound regimes: num_buffers 16 (32 at 4096 agents), cohort_buffers 4, cohort_steps 64, pool workers 24-26 pinned.
Day result: 5M/2048 240K -> 320K, 5M/4096 350K, 15M/2048 263K. Engine stack: mt7 (fast-nle branch tip = mt7 + optional dv4).
- `mask-ablations/`: consolidated results of the September/October mask, passthrough and zero-time-mask ablations
  (MASK_ABLATIONS_RESULTS.md) with each campaign's RESULTS.md, manifest, validation and per-run results.json, plus the 29 Sep audit.
- `repo-live/`: research outputs that lived untracked in the live checkout — resources/article (draft, figures, certificates; logs and
  binaries omitted), scripts/nle_stock (cert LEDGER.md / STATUS.md and drivers), WORK_STATUS.md, NETHACK_OPTIMIZATION_REPORT.md, status notes,
  identify probe tests, and the uncommitted diff of the live tree.
- `repo-worktrees/`: uncommitted diffs of every worktree, the pufferlib-5c commit 7919bbda that exists on no remote (git bundle), small untracked sets.
- `experiment-reports/`: every *.md under /puffertank/experiments (754 files across 111 campaigns).
- `box_archive/`: checkpoint and cert registers. `claude-memory/`: the assistant's project notes (continuity for a new box).
Still host-disk only (~/puffertank/nethack-backup-20261011): checkpoints (480 MB live + 2.7 GB mask policies + 5c/sweep/aux), chat transcripts,
raw results tarball, oracles (1.3 GB action corpus, goldens, reference hashes).
