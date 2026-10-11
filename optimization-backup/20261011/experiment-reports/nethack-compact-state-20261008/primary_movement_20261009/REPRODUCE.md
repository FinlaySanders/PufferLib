# Reproducing the primary movement redesign

Experiment root: `/puffertank/experiments/nethack-compact-state-20261008`.
Final source: `engines/primary_movement/source`. Baseline: `engines/movement_masks/source`.
The `candidate.patch` is relative to that baseline, not upstream or the live checkout.

Build the existing final source with:

```sh
python /puffertank/experiments/nethack-compact-state-20261008/build_engine.py primary_movement
```

The verification build uses the same source and flags plus `-DNH_MOVEMENT_MASK_VERIFY`.
Exact CMake commands are in both engines' `command.json`; `validate.py` builds the
verification variant and invokes the quick suites. Do not recreate source from an
older intermediate copy: the final manifest and patch include the pointer-walk,
room-index, beam-boundary, and scatter-boundary compatibility fixes.

To reconstruct the edits from a fresh copy of the baseline, apply `prepare.py`,
`fix_build.py`, `fix_walks.py`, `fix_border.py`, `fix_rooms.py`, and `fix_scatter.py`
in that order. These scripts expect the named isolated source directory. They are
not intended to run against a live checkout or on already-patched source.

Validation uses immutable fixtures; never regenerate expected hashes:

```sh
python /puffertank/experiments/nethack-compact-state-20261008/check.py --quick primary_movement_verify primary_movement
python /puffertank/experiments/nethack-compact-state-20261008/check.py --hash-only primary_movement_verify
```

The final depth command and environment are in `depth_retry/command.json`; redirect
`CPU_HASHES` and logs to a new directory on a rerun. Compare all 16,777,216 hashes
with `depth/checks/baseline/hashes.bin` and check its checksum against the baseline
result manifest. `complete.py` shows the serialized build/check/timing procedure;
some result directories intentionally reject overwrites.

`screen2.py` imports the existing snapshot harness. Use new run labels when repeating
it: each label maps to a fresh result directory. Both release and comparison variants
first prove the same late-game window against immutable saved hashes. Timed runs use
512 and 2,048 environments in A-B-B-A order with three windows per process. Run no
other builds, profiling, training, or replay workloads concurrently with timing.

The standalone layout test's compiler command is in `layout_command.json`. It checks
all tile coordinates, tile-block alignment, cached-type pointer updates, legacy save
conversion, independent metadata, and cross-column cached-type lookup semantics.
`audit_pointers.py` performs a read-only compiler-assisted audit; its reviewed results
are in `pointer_audit_review.json`.

`finish.py` verifies the completed artifacts and integrity checks, saves the final
patch/manifest/report, and appends the experiment ledger. It does not promote the
candidate, edit production, commit, or push.
