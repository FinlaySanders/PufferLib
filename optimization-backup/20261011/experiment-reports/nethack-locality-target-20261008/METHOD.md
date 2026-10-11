# Locality target experiment

Baseline: the prior glyph16 candidate, which includes the opt61-final recovered
engine and the common message/fire-trap correctness fixes. This is not stock NLE.
Candidate: retain the existing floor-object coordinate index across input keys;
all actual object/level mutation invalidations remain.

Primary CPU comparison: 2048 games, 24 shared-pool workers plus four submitting
threads; same fixed affinity, 8192 warmup decisions per game and 2048 measured.
Actions are the same mature 4B score-policy recordings. The 512 original streams
are duplicated four times; all copies must match. Sample puf_step thread CPU time
at the same dispersed 1/64 decisions. Time both variants twice with interleaved
controls. Native statistical profiles locate executed instructions but do not
measure hardware cache/TLB counters. Profiler overhead is recorded separately.

Diagnostic burst16 executes 16 known recorded actions before switching games.
This is a locality intervention, not a valid online actor collection schedule.
Compare it to ordinary scheduling to locate locality-sensitive work, not to
promise a production throughput multiplier.

Independent counters use 512 streams and only the measured phase. They ran
alongside correctness validation, so their throughput is explicitly excluded.
They count keys, invalidations, rebuilds, floor-object visits and queries.

Behavior gates use the pre-existing unchanged-reference hashes from the previous
study: 34 goldens, 26 fuzz traces, disabled status updates, interleaved/shuffled
multigame replay, and every-decision hashes across 16.8M decisions. Diagnostic
NLE_FOBJ_VERIFY additionally checks the live floor list/order/coordinates on every
indexed lookup. Release builds are checked separately.

Full pipeline comparison: same executable, original 4-buffer inference scheduling,
2048 games, fixed random 5.10M-parameter net, H128, batch262144, PPO minibatch4096.
Run 96 batches; compare elapsed steady-state batches64..94. Recorded mature actions
drive the games. All inference and PPO/optimizer computation executes; actor
writes go to scratch so the policy stays fixed. Compare all96 observation batch
hashes and initial/final weight hashes. This controls compute/workload and is not
a learning experiment or a speed claim for every model/hardware configuration.

All edits/builds remain in the experiment directory. Protected live source hashes
are compared with the prior campaign's baseline before completion.
