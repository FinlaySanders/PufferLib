# Verb-side credit separation: offline protocol

Policy source 3719caaaf945025e4e1e59c6556560d2ba9e3d1c; engine e7f6568568242745a7f7ebd8f730367123522cac. No RL updates or production changes.

1. Enumerated masked epsilon-mixture toy verifies means with deliberately inaccurate critics, item-direction interactions, and score derivatives.
2. Technical pilot: existing middle s27182 takeoff/puton/drop records; independent fit/validation/audit streams. Not a cross-seed replication of a fit using this seed.
3. Expanded logging of all item heads, including exact sampler probabilities, on the same 16,777,216-step early/middle/late streams and second middle action seed. Verify lite and event records against previous captures.
4. Per verb fit a 1024+16 -> 64 -> 64 -> 1 interaction MLP, with state-only and additive controls. Target A_GAE; fit split odd agents except agent%8==7, validation agent%8==7, audit even agents. Normalization only fit data. Auxiliary model seeds 17 and 29. Early stopping uses validation MSE. Correction coefficient selection uses separate validation data (audit untouched). Zero correction remains available.
5. Compare plain GAE, blend toward existing verb critic, centered item-luck correction. Shrinkage uses validation informative episode count n/(n+100); report effective coefficient. Blend coefficient in [0, shrinkage], centered coefficient in [0,1]. Both logit- and parameter-weighted coefficient fits, no audit selection.
6. Report episode and agent-clustered bootstrap intervals, vector mean-gradient shifts, componentwise differences, gradient variance, explained advantage variation, counts and largest-episode sensitivity. Report natural-frequency aggregate over covered verbs. Parameter geometry is exact verb linear decoder (26x1024, no bias); excludes encoder/trunk gradients.
7. Transfer middle fitted critic and coefficients to late checkpoint, retaining source normalization but recentering under target policy. This includes representation drift. Also second middle action-seed transfer on audit streams only (dungeon seed schedules overlap).
8. Gate: replicated parameter ratio <=0.9 with CI excluding 1 on a priority verb, robust to largest episode, and reasonable overhead. No online training without reporting the offline evidence first. A null fitted critic is not a ceiling on all possible critics.

Secondary coefficient diagnostic, added after the first expanded middle-checkpoint bounded audit: also fit an unrestricted signed alpha per item critic, to distinguish lack of predictive direction from critic miscalibration. Held-out evaluation and the same staleness/replication tests apply. Primary remains alpha in [0,1].
