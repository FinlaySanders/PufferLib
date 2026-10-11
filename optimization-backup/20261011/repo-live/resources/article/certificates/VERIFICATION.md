# Verification — 2026-09-13

At the 19:06 UTC snapshot, 24 certificates were imported: 16 fork/stock C,
four completed 4,032-game Python runs, and four historical 480-game Python runs.
Both 2B 4,032-game Python certificates remained pending in this snapshot.

Every imported C certificate's selected count, rounded mean, mean SE and median
matches `vendor/fast-nle/stock/analyze.py`. Every imported Python certificate's
count, rounded mean and median matches that tree's `gym_analyze.py` equal-k
headline. The ledger additionally checks the expected number of workers and the
complete episode sequence in each worker.

An in-memory missing-worker case and an incorrect file hash both raised errors.
The article generator refused to regenerate figures while `2B/gym` was pending.
No new game evaluations were launched for this verification.

The launch logs contain an automatically appended claim that an episode-1 versus
later-episode median difference is a state leak. That annotation is retained as
historical evidence, not endorsed as an inference by this ledger.

## 21:13 UTC update

Both 2B 4,032-game Python certificates were imported and passed the worker-count, episode-sequence and input-hash checks. Their counts, rounded means and medians also match gym_analyze.py. The 8,064-game pooled 2B result is median 10,345 and mean 16,752.84. All headline groups are now complete. Article JSON/CSV and the generated C data header were refreshed; PNGs were not regenerated.
