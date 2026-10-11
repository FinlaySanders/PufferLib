# Floor-object block bounds

Parked after the short CPU screen: control214560SPS, candidate215095SPS (+0.249%). This is below the predeclared0.8% gate for reverse-order confirmation.

The candidate adds conservative rectangles around32 consecutive entries in the existing ordered floor-object index. A query skips a block only when its bounds are disjoint. Index order, eligibility, RNG and mutation fallback remain unchanged. Added metadata is512bytes per game.

Both ordinary-GCC/LTO builds passed582201queries against the scalar reference, including extreme/inverted/changing bounds, tails, overflow and invalidation. Property-output hashes match. Each native2048 process ran two restored512-decision timing windows. This is one control/candidate pair, not a confidence interval or a full-training comparison.

No PGO rebuild, full-corpus proof or production change is justified by this result. Commands, source hashes, patch and property logs are in this directory; raw replay artifacts are in ../native_pool/runs/box_{control,candidate}_0/.
