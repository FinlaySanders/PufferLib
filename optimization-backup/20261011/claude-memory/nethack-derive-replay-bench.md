---
name: nethack-derive-replay-bench
description: "Offline unit-test bench for the stock-NLE reconstruction (nh_derive.h): harness recorder NH_DERIVE_REC + nh_derive_replay; how to use it, its limits, and the first bugs it found (2026-09-12)"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-09-12T10:47:17.575Z
---

The reconstruction layer (`scripts/nle_stock/nh_derive.h`) has an offline test bench since 2026-09-12 (`53d051ea`, `0cf32001`):
- **Record**: `NH_DERIVE_REC=<dir> NH_DERIVE_REC_ENVS=<n>` on `puffer_nethack_harness` in mode 0 writes one `.drec.gz` per episode (every env key, every probe reply, boundary refreshes, fork truth at every hook; block-delta + gzip ≈ 2 MB/episode). Build a recorder binary beside the ablation one with `OUT=... build_vec_harness_nh.sh` so a running ablation's binary is never touched.
- **Replay**: `bash scripts/nle_stock/derive_replay.sh <dir>` (one `nh_derive_replay` per core, merged table, examples, `BASE=<merged.rates>` diff → `REPLAY_OK`/`REPLAY_REGRESSION`). ~30 s for 176 episodes on 32 cores. `nh_derive_replay --watch <channel> <file>` prints each change of the real value with the last messages: the fastest way to find the message a belief misses.
- **Validated**: replay == live harness table exactly (18 channels, queries and mismatches) on 176 episodes.

**Why:** a derive fix used to cost an hour-long live eval per iteration and gave only aggregate mismatch rates; the user asked for a test-and-iterate loop ("this feels like the type of thing we can easily write tests and quickly iterate on").

**How to apply / limits:**
- A change to *what the derive probes* (new probe trigger, periodic re-probe) diverges from the recording from that step on; the episode is skipped and counted (`diverged=`). Re-record the corpus after probing changes and validate them live; parsing/logic fixes replay exactly.
- The reader must keep a pristine copy of the recorded observation separate from the buffers the derive writes into (`dr_restore`), or block-deltas drift (first bug of the bench).
- The recording carries the `NH_*`/`NLE_*` environment; the derive caches its switches on first use, so the replayer applies it before the first call (a replay without `NH_STOCK_TERRAIN_PROBE=1` diverged at the first terrain probe).
- Corpora live in `/tmp/drec` (old derive) and `/tmp/drec2` (fixed derive), seed 99, 128 agents; regenerate with the recorder in ~4 min.

**First findings (old derive, mismatch per query):** capacity 6.7 % ("You strain a muscle" wounds a leg; heal text was the 3.4 one), path 5.2 % (BFS vs actual run corners), food underfoot 2.4 % (top object only; fork scans the pile), weight 1.3 % (unidentified appearance weights: not public), intrinsics 0.25 % (polymorph form parser never matched: form is in parentheses of the farlook line). Capacity → 0.13 %, food/containers → 0, intrinsics → 0 after `0cf32001`. Related: [[nethack-cert-ledger]], [[nethack-stock-nle-bridge]], [[nethack-challenge-binding]].

**2026-09-12 afternoon — record a corpus with the policy you are certifying.** The 1B corpus never exercised two 2B failure modes: weight goes wild while hallucinating (NLE randomises inventory glyphs; the glyph fallback priced boulders into the pack, 4.9 % of late-game steps) and the one welcome line longer than 80 columns (neutral female gnomish Archeologist) wraps and was never parsed (1 % of games). Both fixed in `2f302173`. Use a long recording (128 envs × 25 min, `eval_episodes` huge, `timeout`) and `MT=5000` for late-game rates. Harness score arms (`derived`, `real0`) are NOT stock proxies (−48 %, −37 % on the fork vs −11 % on stock); only mode-0 recordings and mismatch tables are valid.

**2026-09-12 16:20 — lessons from the v2 replay.** (1) A replay whose rates are byte-identical to the previous one did not run the new code or the new
code never fires — check raw counts, not the DONE line; that DONE line had re-read the old output directory. (2) The bench IS faithful for weight:
stock NLE hides object types in every glyph (`winrl.cc shuffled_glyph`) exactly like the fork, so the fork-recorded appearance glyphs are what stock
shows too; the 2.9 % weight mismatch is real and not derivable (the fork exports true-type weights). Verify engine-side claims on the running engine
(`NH_STOCK_WTCHECK` in the stock backend: 3 minutes). (3) Identity: the 80-column welcome line carries a `\n` at the tty wrap inside the message
buffer — tokenizers must treat newlines as spaces (`5ee2c435`). (4) `build_derive_replay.sh` ignores `OUT=` and writes in place. (5) `--watch <channel>`
piped through awk for `new != derived` finds the first divergence with its messages in seconds; do that before theorising.
