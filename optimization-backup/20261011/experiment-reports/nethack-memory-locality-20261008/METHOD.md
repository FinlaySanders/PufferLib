# Memory-locality screen, 8 October 2026

The baseline is the already-optimized opt61-final engine, including the common message initialization and fire-trap HP fixes. Changes are isolated here; no live trainer or game files are edited.

CPU cases replay the same 512 recorded policy streams, duplicated four times for 2,048 resident games. Four submitters use a shared 24-worker pool. Games warm for 8,192 decisions before measuring 2,048 decisions. The ending mean game age is 29,502 turns. Sampled thread CPU time covers a deterministic, dispersed 1/64 of decisions. Baseline pinning maps eight workers to P cores and sixteen to E cores; submitters use four P-core siblings.

All screening cases compare final observations for each duplicate and the normalized aggregate observation hash, plus world-turn advance totals. Any candidate retained needs the longer per-action hash check (observations, rewards, terminals, action masks) and golden/fuzz replay. Timings exclude verification hashes. This is a bounded behavior check, not an exhaustive proof.

The source-layout tests each change one area:

- `hotctx`: small game fields, lazy-buffer pointers and player state placed ahead of large arrays. No field meaning changes.
- `hotrl`: status/inventory metadata placed before the large window-port arrays. No field meaning changes.
- `glyph16`: internal display entries use a signed 16-bit glyph with a compile-time range check; entry size drops from 8 to 4 bytes.
- `huge_ctx`: diagnostic aligned 2 MiB allocation per game state with MADV_HUGEPAGE. It deliberately spends more RAM; check smaps for actual huge pages. It changes allocation/reset cost and alignment too, so a gain would need further attribution.
- `CPU_NO_SUBMIT`: control with the same 24 workers but no help from the four submitting threads.
- `CPU_STICKY=2`: pinned, fixed ownership, P workers given twice the lanes of E workers. No stealing; can lose load balance.

Native statistical profiling starts only after warmup. Its sample shares locate hotspots, not cache-miss counts. Hardware perf events are unavailable on this host. Historical Callgrind cache simulation is only a lead, not a hardware measurement.

If an engine change wins, repeat its timing bracketed by the baseline and test full training with the original four-buffer inference layout. Do not mix an inference-partition change into an engine-only comparison: earlier work showed different GEMM shapes change floating-point outputs and some sampled actions.

The profile-guided follow-up `fobj8` stores floor-index x/y coordinates as signed bytes (matching the engine xchar coordinate range) and tests sixteen rather than eight entries per SSE2 comparison. It preserves iteration order, cache invalidation and linked-list fallback. This changes both data footprint and instructions per tested item; its effect cannot be attributed to cache alone. `compact` combines this with `glyph16`.

For the modern-observation golden gate, historical recorded actions are copied into this directory and repinned **only against the unchanged baseline** using NLE_REPLAY_UPDATE. The candidate then runs in strict comparison mode. Historical originals and engine observation code are untouched. This is behavioral equivalence to our baseline, not a new claim of byte equality to stock observations.

Full-pipeline check: the existing puffer_all benchmark binary, 2,048 environments, original four buffers, horizon 128, rollout batch 262,144, PPO minibatch 4,096. A fixed random 5.10M-parameter model performs inference and the complete training calculation; recorded mature actions supply the same environments. The optimizer writes scratch parameters, keeping rollout weights unchanged. Timing covers epochs 64 through 94 after 8,192 decisions/game of warmup; 96 epochs are executed. This is a controlled compute-throughput benchmark, not a learning experiment or a trained 5M policy.

Affinity caution: fixed ownership changes P/E work distribution and processor utilization as well as locality. Its lower sampled CPU time is not a pure cache measurement. End-to-end throughput is the acceptance metric, and it regresses badly.
