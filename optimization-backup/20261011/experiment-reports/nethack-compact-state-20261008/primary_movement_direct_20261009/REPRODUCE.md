# Direct primary-cell query

Root: `/puffertank/experiments/nethack-compact-state-20261008`.
Source: `engines/primary_movement_direct/source`.

This source contains the corrected primary-layout migration documented in
`../primary_movement_20261009/REPRODUCE.md`, followed by its `prepare_direct.py`.
That last step replaces per-query flag-word construction with direct cell reads
and conditional predicates. Writers, storage, saved-format conversion, and the
boundary compatibility fixes are unchanged.

Build with `python ../build_engine.py primary_movement_direct` from this directory.
`validate.py` builds the original/new-query comparison variant and runs both sets
of quick tests. Engine directories contain exact CMake command JSONs. `run.py`
serializes the quick gates, full score/depth checks, then `screen2.py`.

Full reference-comparison results live in:

- `../checks/primary_movement_direct_verify.json`
- `../depth/checks/primary_movement_direct_verify/result.json`

The expected hashes are the same immutable score/depth captures used by the
predecessor experiment. Never regenerate them. Use new result labels/directories
on reruns; scripts deliberately reject some overwrites. No concurrent builds,
profiling, training, or replay workloads should run during native timing.

`layout_command.json` rebuilds the standalone layout test against this variant.
The tile header, pointer-update macro, and pointer-walk migration are identical
to the predecessor; its compiler-assisted pointer audit is included with its review.
`screen.json` and `trials.csv` retain all paired native timing measurements.
`finish.py` creates a source manifest, patch, report, and ledger entry. Nothing here
edits production, commits, pushes, or promotes the candidate.
