# Offline verb-conditioned residual critic

Written before fitting or inspecting the new audit results. Production training
code and checkpoint weights remain unchanged.

Predict Delta(s, v) from detached, pre-action 1024-dimensional recurrent features.
Target is the captured training-convention GAE advantage; thus Q = V + Delta.
Only the selected verb output is supervised. Actor arguments would use A-Delta;
the verb would keep A. Test only unclipped, on-policy gradient estimators here.

Data: existing fixed-step early/middle/late captures and second middle seed.
They contain full features for wear, quaff, zap, put-on, read, not all 26 verbs.
The output layer has 26 entries, but claims are restricted to those five.

Split entire environment streams: train odd agents except agent % 8 == 7;
validation agent % 8 == 7; audit even agents. No episode crosses a split.
Keep prior fixed warm-up and horizon-boundary exclusions. Test transfer of the
middle-seed-31415 fits on all seed-27182 streams without refitting. Rollout seeds
are different sampling streams with the same indexed environment-seed schedule,
not guaranteed independent dungeon seeds or independently trained policies.

Compare baseline A, a verb-wise constant, fitted centered verb-logprob control,
linear residual, and a 128-hidden-unit ReLU MLP residual. The two learned models
minimize ordinary MSE, balanced and target-scaled by verb. A secondary identical
MLP minimizes item-score-norm-weighted MSE, which targets gradient second moment
more directly. All baselines at inference depend only on state and verb.
Use AdamW, lr .001, weight decay .001, batch 256 per verb, maximum 1500 updates,
validation every 50 updates, and the initial zero predictor as a candidate.
Stop after 400 updates without validation improvement. Two MLP initialization
seeds (17, 29); linear seed 17. Select by validation objective, never audit.

Report each method separately, not the best audit result. Primary learned
advantage is A-Delta with coefficient one. No audit-fitted scaling or clipping.
Report held-out MSE and gradient trace-variance ratios per consumed head, paired
95% bootstrap intervals over episodes and environment streams (conditional on
the fitted model). Logit scores use the exact captured masked sampling logits.
Include zap direction-head results with the same verb baseline, and a put-on
decoder-parameter check on a fixed random audit subset. Bootstrap intervals do
not include critic-fitting uncertainty; initialization repeats expose some of it.

Do not claim online PPO improvement or general unbiasedness after PPO clipping.
The decision is whether the learned baseline warrants a subsequent controlled
online implementation, not whether these offline fits improve playing strength.

## Scope expansion requested during the first pass

Extend the fixed-step captures to other consumed verbs, including movement,
throwing, eating, applying tools, and spell casting. Same checkpoints and
16,777,216 steps per capture. An independent deterministic hash samples common
verbs: movement/run and argument-free verbs 1/64, throw 1/8, eat/drop 1/4;
all other argument events are retained. Complete lightweight streams supply
GAE and unbiased verb frequencies. No event is selected using its outcome.
The changed logger passed a 212,992-transition byte-for-byte comparison of all
lightweight records and 1,098 overlapping full records with the prior logger.

Keep the first five-verb study, including its unfavourable results, as a
separate first pass. Full-verb models train on argument-consuming verbs only.
Add a state-only residual MLP with the same capacity as a control for ordinary
value-function improvement. It has one output and a common target scale.
All-verb extension uses the original fit/validation/audit split and fitting
settings. After the primary fits, examine validation-only shrinkage of each
verb's correction as a clearly labelled secondary method, not a replacement
for reporting the raw learned baseline.

The first shared fits often selected the zero predictor or the first saved
checkpoint. Add independently trained per-verb 128-unit critics, selected on
that verb's validation samples (also save updates 5, 10, 20), to distinguish
shared-fit compromise from unavailable predictive signal. Report them as a
higher-capacity diagnostic, not the same cheap 26-output implementation.
These are separate ordinary-MSE and score-norm-weighted fits, seed 17. They
receive exactly the same pre-action trunk features. No audit selection.

The first state-only control used the same verb-balanced batches as the
conditional critics. That changes its target's verb mixture, so also fit a
state-only control with inverse-logging-probability weighting over all verbs,
including no-argument verbs. This is the appropriate comparison to improving
the ordinary state-value predictor. Retain both controls in the raw results.

Replicate all middle-checkpoint argument heads on rollout seed 27182 with
frozen critics fitted on seed 31415. Additional pointer-activation logging for
take-off, put-on and drop enables a true decoder-parameter subset check on the
replication set. Added pointer logging preserves every record in a 212,992-step
smoke comparison. Keep the initial three-stage analyses and transfer separate.
