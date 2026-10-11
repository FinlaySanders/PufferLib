# Direct training of centered item differences

Offline follow-up to verb_credit/REPORT.md. No policy updates, new rollouts, or production-code changes.

Question: did ordinary prediction loss hide a useful within-state item signal?

For each state/verb, predict f(s,v,i) for every legal item. Form c_i=f_i-sum_j mu_j f_j *inside the training graph*, differentiating through both f terms. Probabilities, features and policy are frozen.

Minimize mean w*(c_chosen^2 - 2*A*c_chosen), equivalent to weighted MSE against A with the constant target-square term removed. State-only output offsets cancel. Primary: same 64x64 item-interaction MLP and normalized inputs as the previous study, MSE seeds 17/29. Secondary: parameter-score-norm weights, seed 17; and weighted fit with frozen state/verb prediction removed from the target. These target variants have the same population centered optimum; finite-sample behavior may differ.

Use existing 131M/524M/1B captures, plus second 524M action seed and 524M->1B transfer. Fit odd streams except agent%8==7; validate on agent%8==7; audit even streams. Never select using audit data. Reusing the same audit data after a null is an exploratory follow-up, not a fresh independent confirmation.

1200 maximum AdamW updates, batch 512, lr .001, weight decay .001, stop after 300 updates without validation improvement. Zero predictor remains a candidate. Compare matched old ordinary-Q critics on identical audit events. Fit bounded [0,1] and unrestricted alpha on validation only, and also show unscaled alpha=1 so shrinkage cannot conceal predictor failure. Select model checkpoints using centered validation loss; report unscaled and calibrated gradient variance separately.

Validate masked centering, cancellation of state-only offsets in both outputs and training gradients, and a planted state-item interaction on real saved features with noise. A failed positive control blocks a substantive null interpretation.

Audit full verb decoder parameter gradients and logit gradients, episode and stream clustered 95% intervals, top-episode removal, mean-gradient differences, and validation/test mismatch. Transfer freezes normalization, critic and alpha and re-centers under target probabilities.

Prioritize quaff, read, zap, puton, wear, throw; retain takeoff/drop comparisons. Existing online gate unchanged: a replicated >=10% parameter-variance decrease with CI below 1 and robustness to outliers. No online training in this follow-up.
