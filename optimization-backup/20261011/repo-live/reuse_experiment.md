PufferLib 5 reuse diagnostics: instructions for the coding agent
2 Oct 2026 · @Fin
Goal and ground rules
Add logging-only diagnostics to the PufferLib 5.0 trainer to find out why performance degrades as replay_ratio rises. Do not change the training algorithm; every task below measures, it does not fix (Task 6 is the one opt-in exception).
• Flags. Gate everything behind train.diag (default 0) in config/default.ini, parsed into Hypers like the other [train] keys. Task 2 has its own flag, train.diag_holdout (default 0), because it removes data from training.
• Off means off. With diag = 0, launch no extra kernels and leave training output unchanged.
• On means logging only. With diag = 1 and diag_holdout = 0, training numerics must match diag = 0.
• CUDA graphs. Any value that changes per minibatch (pass index, bucket pointers) lives in device memory, following the existing ent_coef device-pointer pattern. Accumulate on device; copy to host only at log time, alongside the existing pufferl->losses copy.
• Overhead. Keep the SPS cost of diag = 1 under 3%, and report the measured number.
• Hands off. Do not edit the PPO loss math, the advantage math or the optimizer except to read values out of them.
Where the code lives
All hooks are in two files, src/pufferl.cu and src/algo.cu. Names below are from the 5.0 branch; confirm each before editing.
What
Where
Notes
Minibatch loop
src/pufferl.cu, train step
Minibatch count is replay_ratio × batch / minibatch. Each minibatch takes a fixed slice, dest_off = (mb * mb_segs) % n_rows, so every pass revisits the same slices in the same order.
Advantages
src/algo.cu, puff_advantage
Called per minibatch with live values (graph.mb_gae_v) and, if V-trace is on, graph.mb_imp. Uses R_{t+1}, D_{t+1} indexing.
Per-sample logits walk
src/algo.cu, cache_imp_and_v
Has each head's cache[a] and lse; writes the new log-prob and the ratio. NetHack's verb head goes through nethack_verb_train_logp (epsilon-mixed).
PPO loss
src/algo.cu, ppo_loss_compute
Computes ratio, clip fraction and approx KL per sample, then reduces into losses_acc via ppo_loss_reduce. The gradient is zeroed where d_ratio is set to 0.
Loss slots
LossIdx in src/algo.cu, LOSS_NAMES[] in src/pufferl.cu
The two must stay in sync.
Logging
src/pufferl.cu, losses_host block
Divides by the minibatch count in slot LOSS_N, then dict_set per name.
Optimizer
src/algo.cu, muon_step
m->grad_norm holds the sum of squared gradients before the global clip in muon_clip_nesterov.
Config
config/default.ini [train]; Hypers and puf_ini_get in src/pufferl.cu
Add new keys with defaults and a one-line comment.
Task 1: Per-pass drift
This answers whether PPO's clip actually stops the policy moving under Muon and momentum. Every existing loss is currently averaged over the whole epoch; break it out by replay pass.
1. Pass index. p = floor(mb / minibatches_per_pass), where minibatches_per_pass = n_rows / mb_segs. Cap at 16 buckets; later passes go into the last one. A fractional replay_ratio leaves a partial last pass, so keep a minibatch count per bucket.
2. Per-pass loss buckets. Add a device array [16][NUM_LOSSES]. In ppo_loss_reduce, add each minibatch's partials into the current pass bucket as well as the existing accumulator. This gives per-pass approx KL, old approx KL, clip fraction, mean ratio, policy, value and entropy loss.
3. Gradient actually zeroed. In ppo_loss_compute, count samples where d_ratio is set to 0. This differs from clip fraction, which also counts samples outside the range that still carry gradient.
4. Log-ratio histogram. 64 bins over log r in [−1, 1], plus underflow and overflow bins, one histogram per pass, filled with atomicAdd in ppo_loss_compute. On the host, compute the 1st and 99th percentiles and the fraction outside [log(1−ε), log(1+ε)].
5. Pre-clip gradient norm. After muon_sum_sq_reduce in muon_step, a one-thread kernel adds sqrt(grad_norm) into the pass bucket. Also count steps where it exceeds max_grad_norm.
Log keys, one set per pass p:
• diag/pass{p}/kl, diag/pass{p}/clipfrac, diag/pass{p}/zeroed_frac
• diag/pass{p}/logratio_p01, diag/pass{p}/logratio_p99, diag/pass{p}/outside_frac
• diag/pass{p}/grad_norm, diag/pass{p}/gradclip_frac
• diag/pass{p}/drift_rate, computed on the host as (kl(p) − kl(p−1)) / minibatches_per_pass
How to read it. Under plain SGD, the gradient norm falls as zeroed_frac rises, and drift slows with it. If the gradient norm falls but drift_rate stays roughly constant, Muon's normalisation has removed that brake.
Task 2: Held-out slice
This answers whether the policy drifts more at states it never trained on, and whether the critic overfits. It runs only with diag_holdout = 1, because it removes one slice of data from training.
1. Frozen targets (part of diag = 1, not just holdout). At batch start, compute advantages and λ-returns once for every row from the rollout-time values, using puff_advantage with V-trace off. Store them as adv_frozen and ret_frozen. They are for diagnostics only; training keeps its live-value targets. Tasks 3 and 4 reuse them.
2. Reserve a slice. Hold out the last mb_segs rows of each batch, which is one minibatch slice. Training slices cycle over the remaining rows instead of n_rows. If fewer than 16 slices remain, disable holdout and log a warning.
3. Evaluate at each pass boundary. Run a forward-only pass on the held-out slice through the same path as training (arch_forward_train, then cache_imp_and_v), with no backward pass and no optimizer step. Use the stored initial recurrent states for those rows, as training does. Run it outside any captured CUDA graph; one host-side call per pass is fine.
4. Compute. Approx KL to the rollout log-probs, using the same estimator as training; the fraction of log-ratios outside the clip range; and value MSE against ret_frozen. For a fair comparison, also accumulate training-side value MSE against ret_frozen on the minibatches of the same pass.
Log keys, per pass:
• diag/pass{p}/heldout_kl, diag/pass{p}/heldout_outside_frac
• diag/pass{p}/heldout_vmse, diag/pass{p}/train_vmse_frozen
How to read it. If heldout_kl tracks kl from Task 1, drift is confined to what training can see. If it grows faster, the policy is moving at unseen states. If heldout_vmse rises while train_vmse_frozen falls, the critic is overfitting the batch.
Task 3: Critic absorption
Puffer recomputes advantages from the live value function on every minibatch. This answers whether the critic memorises the batch and erodes the advantage signal across passes. It needs diag = 1 only.
1. After puff_advantage in each minibatch, reduce over mb_advantages: mean |A|, mean A² and mean A, which should stay near 0.
2. On the same rows, accumulate Σ A_live·A_frozen, Σ A_live² and Σ A_frozen², using adv_frozen from Task 2 step 1.
3. Bucket all of it by pass, as in Task 1.
Log keys, per pass:
• diag/pass{p}/adv_abs, diag/pass{p}/adv_mean
• diag/pass{p}/adv_abs_ratio: mean |A_live| / mean |A_frozen|
• diag/pass{p}/adv_corr_frozen: Σ A_live·A_frozen / √(Σ A_live² · Σ A_frozen²)
How to read it. adv_abs_ratio falling well below 1 across passes means the critic is absorbing the signal. adv_corr_frozen dropping means the advantage targets are moving during reuse. Either one is a reason to freeze advantages at batch start.
Task 4: Control-variate correlation (log only)
This answers how much TD-error variance comes from action sampling, and so whether a control variate is worth building. Nothing computed here feeds back into training. It assumes vtrace = 0, the default.
1. Define c_t. For each sample, c_t = Σ over the heads h used at t of [log π_h(a_h|s_t) + H(π_h(·|s_t))], under the current policy. Use the same distribution that actions are scored with; for NetHack's verb head that is the epsilon-mixed distribution in nethack_verb_train_logp, so compute the mixed probabilities for every verb and take their entropy. Skip heads where nethack_head_used is 0. By construction, c_t has mean zero under that distribution.
2. Write it. In cache_imp_and_v, write c_t to a new scratch buffer of shape [B, T].
3. Correlate with one-step TD errors. In a side kernel over the same minibatch, compute δ_t = r + γ·V(s_{t+1})·(1 − d) − V(s_t) from the same live values, with the same R_{t+1}, D_{t+1} indexing as puff_advantage. Pair c_t with δ_t at the same index, the step whose action c_t scores. Accumulate Σδ², Σδc and Σc² per pass.
4. Measure what matters: the advantage sum. Keep a device scalar α, set at each log step to the latest cv_alpha (0 at start). In the same side kernel, run the corrected recursion without writing to any training buffer: A*t = (δ_t − α·c_t) + γλ·A*{t+1} and Â_t = δ_t + γλ·A*_{t+1}. Accumulate the variance of the plain GAE advantage and of Â_t.
Log keys:
• diag/cv_corr = Σδc / √(Σδ² · Σc²), plus diag/cv_corr_pass0 from the first pass only, the closest to on-policy
• diag/cv_alpha = Σδc / Σc²
• diag/adv_var_gae, diag/adv_var_cv
How to read it. One-step variance left after correction is about 1 − cv_corr², so below 0.3 the control variate can wait. The deciding number is adv_var_cv / adv_var_gae, because that is the variance the policy update actually sees.
Task 5 (optional): V-trace double count
Run this only in runs with vtrace = 1. With both clips at 1, Puffer's policy advantage works out to min(r_t, 1) · (δ_t + γλ·A_{t+1}), and the PPO loss then multiplies by r_t again. This measures how much that matters.
In ppo_loss_compute, over samples with advantage > 0, accumulate per pass the count with r < 1 and the sum of min(r, 1).
Log keys, per pass:
• diag/pass{p}/vtrace_pos_lt1_frac: share of positive-advantage samples with r < 1
• diag/pass{p}/vtrace_pos_minr: mean min(r, 1) over positive-advantage samples
How to read it. A mean of 0.95 or more means the double count barely matters. Values near 0.6–0.7 late in reuse mean it does, and V-trace deserves a fair retest once fixed.
Task 6 (optional): KL early-stopping baseline
This is the one behaviour change in the list, and it is the cheapest fix any new method has to beat. It is active only when train.target_kl > 0 (default 0, off).
1. At each pass boundary, read the on-batch approx KL for the pass just finished from its Task 1 bucket. One host sync per pass is acceptable.
2. If it exceeds target_kl, skip the remaining minibatches for this batch and move on to the next rollout.
Log keys:
• diag/passes_used: passes completed this batch
• diag/early_stopped: 1 if the batch was cut short, else 0
Runs and what to report
Run the three sets below on Breakout as the fast environment and NetHack as the hard one. Use each environment's tuned config, changing only the listed keys, with the same total_timesteps across replay ratios. NetHack's tuned replay_ratio is 1.78, so 4× is about 7.
Set
Purpose
replay_ratio
Flags
Seeds
A
Find the leak
tuned, and 4× tuned
diag = 1, diag_holdout = 1
2
B
Degradation curve
1, 2, 4, 8, 16
diag = 1
3
C
Early-stop baseline
1, 2, 4, 8, 16
diag = 1, target_kl = 0.01 and 0.02
3
Report back:
1. Set A per-pass table at 10%, 50% and 90% of training. Columns: pass, kl, drift_rate, zeroed_frac, grad_norm, heldout_kl, adv_abs_ratio, adv_corr_frozen, train_vmse_frozen, heldout_vmse.
2. Final score against replay_ratio for sets B and C, as mean ± standard deviation over seeds.
3. cv_corr, cv_alpha and adv_var_cv / adv_var_gae over training, from set B at the tuned ratio.
4. SPS with diag off and on, with holdout cost reported separately.
5. Raw logs for every run as CSV.
Acceptance checks
Pass all of these before reporting any results.
[ ] No behaviour change when off. With diag = 0 and a fixed seed, logged losses for the first 20 epochs match the pre-change build. If existing atomics already make runs nondeterministic, report the run-to-run spread and match within it.
[ ] Logging only when on. With diag = 1 and diag_holdout = 0, training losses match diag = 0 within that same spread.
[ ] Bucketing is right. In synchronous mode, pass 0's first minibatch shows KL ≈ 0 and mean ratio ≈ 1, because the data is fresh. In async mode, expect a small non-zero value.
[ ] Histograms are complete. Each pass's histogram counts sum to the samples processed in that pass.
[ ] Frozen matches live at the start. On pass 0, minibatch 0, live advantages equal adv_frozen on the same rows.
[ ] c_t is zero-mean. On pass 0, |mean c_t| is much smaller than its standard deviation.
[ ] Overhead. diag = 1 costs under 3% SPS, measured and reported.
[ ] Config documented. Every new ini key has a default and a one-line comment in config/default.ini.