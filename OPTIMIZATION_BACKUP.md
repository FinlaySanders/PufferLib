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
