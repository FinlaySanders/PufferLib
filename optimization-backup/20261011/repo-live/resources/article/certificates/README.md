# NetHack results ledger

This directory is the source for the fixed-weight 1B, 2B and 4B article results.
`RESULTS.md` is the readable table; `results.json` and `results.csv` contain the
same computed statistics. `manifest.json` identifies every input, its source,
SHA-256, checkpoint and available launch evidence. `raw/` contains byte-for-byte
snapshots, so reproduction does not depend on `/tmp` or a running drone.

Run from any directory:

```sh
python3 /puffertank/pufferlib/resources/article/certificates/ledger.py refresh
python3 /puffertank/pufferlib/resources/article/certificates/ledger.py build
```

`refresh` reads completed certificates from the existing drone queue and imports
the earlier local 480-game Python certificates. It never starts an evaluation.
`build` is offline and checks input hashes and episode counts before computing
anything. Do not hand-edit generated tables or copy numbers from console panels.

## Selection and statistics

- Fork: each training seed's eval seed 7 certificate; discard the first 4,000
  completion-ordered rows and take at most the next 10,000, matching `analyze.py`.
- Stock C: eval seeds 21 and 32 for 1B/2B; seed 21 for 4B. Apply the same
  `analyze.py` slice. Runs targeted 10,000 total games, so approximately 6,000
  remain, including completion overshoot. No outcome-based exclusions.
- Python headline: both training seeds, exactly 144 workers × 28 episodes per
  seed (4,032 games). Every worker must have all episodes, numbered 1 through 28.
  No burn-in removal. An incomplete pair is **pending**, never a one-seed pool.
- Earlier 24 × 20 Python runs are preserved as historical results, separately.
  They are never silently substituted for the larger headline certificates.
- Pool episode scores, not seed medians. Mean SE is population standard deviation
  divided by sqrt(n), as in `analyze.py`. It describes episode sampling, not
  uncertainty across training seeds. Quantiles use sorted[floor(p*n)], matching
  `gym_analyze.py`; medians use the standard midpoint for even samples.
- Keep all recorded terminal statuses. Status counts are descriptive: a heuristic
  `aborted` label in the old logs is not a reliable diagnosis of an engine crash.

## Limits of the evidence

The raw files establish scores and recorded outcomes, not absence of observation
leaks. Build identifiers in launch lines are historical provenance, not a fresh
binary audit. A checkpoint hash collected now identifies the retained artifact;
the original launch log did not record a full checkpoint hash.

Stock C and Python used real wall clock in these certificates; fork used its
seeded calendar. These are not pinned-clock trajectory pairs, nor formal
equivalence tests. Historical calendar diagnostics do not establish the cause of
the remaining differences. First-episode versus later-episode median differences
alone do not establish a cross-episode state leak.

AutoAscend reference numbers are deliberately excluded from this ledger until
their primary sources and comparison protocol are verified. Legacy leaky models,
clock ablations, smoke evaluations and training-panel scores are outside this
fixed-model headline dataset. Existing PNGs and the article prose are snapshots;
they are not authoritative until regenerated from a complete ledger.
