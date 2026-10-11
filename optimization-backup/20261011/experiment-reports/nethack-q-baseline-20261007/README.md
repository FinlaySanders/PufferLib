# Online verb-conditioned argument baselines

Approved experiment: four paired seeds, 1B steps per model, three arms, all trained from scratch. For each seed the order is **control → all_arguments → takeoff_puton**. Seeds are 4101–4104. No checkpoint is used to initialize an actor or critic. Total requested training: 12B steps.

| Arm | Auxiliary critic | Correction |
|---|---|---|
| control | Trained, detached | Off |
| all_arguments | Same critic | Every consumed item, direction, and spell head |
| takeoff_puton | Same critic | Takeoff item head 6 and puton item head 7 only |

The verb head is never corrected. Unconsumed argument heads remain gated off. The actor architecture, parameters, masks, exploration schedule, rewards, Muon optimizer and PPO settings match the frozen baseline. The auxiliary network has its own AdamW optimizer and never updates the trunk. Actor checkpoints remain compatible with the existing evaluator.

## Implementation

The critic predicts the GAE residual b(s,v), equivalent to Q(s,v) = V(s) + b(s,v), for all 26 verbs. It is a 128 → 128 → 26 MLP (26 live outputs, padded to 32), tanh hidden activations, zero-initialized output layer, 160,032 auxiliary parameters. This is a new online critic, not an imported offline tree or checkpoint.

Inputs are the detached 1,024-dimensional recurrent feature, normalized by its per-row RMS, plus causal history: current V, episode age, horizon position, previous verb, and value changes/past clipped rewards at lags 1, 2, 4, 8 and 16. A 64-channel history block is padded with zeros. Current sampled item, direction and subsequent reward are not inputs. Explicit role one-hot and offline fitted standardization are not used; this differs from the offline model. No claim of a direct offline-to-online architectural replica is intended.

Predictions are computed before sampling and retained with the rollout. The auxiliary actor snapshot is frozen for that rollout. Async collection uses separate buffers from the learner. The critic trains after the actor epoch, once over the saved rollout features, targeting production CUDA GAE from frozen rollout V and total BF16 rewards clipped to [-1,1]. Gamma/lambda are unchanged. Last-horizon-index targets and controls are zero, matching the trainer's boundary convention. MSE is averaged per verb with count+8 smoothing. AdamW: lr 0.0003, betas 0.9/0.999, weight decay 0.01, global gradient norm cap 5. No gradients are computed for critic inputs.

### PPO correction

Simply replacing A inside PPO's clipping decision would change the objective. This implementation retains the original clipped PPO loss and adds, only to the selected argument gradients, the loss-gradient control:

`+ b_old(s,v) * (current_joint_probability / behavior_joint_probability) * grad(log current_argument_probability)`

The coefficient is fixed at 1. The correction has no PPO clipping gate. Conditional on state and verb its expectation over arguments is zero, including when the verb uses both an item and a direction. The ordinary PPO branch, verb gradient, value loss and entropy loss are unchanged. PPO itself retains its existing BF16 behavior log-probability; the added control uses a separate FP32 copy written by the actual sampler, including epsilon mixing and only the consumed heads. Numerator is the current full consumed-head joint probability. The reported PPO scalar loss remains the original objective; correction diagnostics are separate.

This is an expectation statement under fixed policy distributions, not a promise that finite-batch updates or resulting checkpoints will match. Online learning benefit remains unproven.

## Validation

- Actual auxiliary CUDA forward/backward checked against independent float64 PyTorch and finite differences.
- Actual modified PPO CUDA kernel checked against autograd, including masked actions, epsilon-mixed verbs, item+direction choices, spell choices, on-policy and changed-policy ratios, and PPO clipping.
- Exact enumeration confirms the added expected gradient is zero; a planted conditional-offset test confirms variance can decrease.
- 2,097,152-step reference, disabled, control and both active-arm smokes. Reference = disabled = auxiliary-control actor checkpoints **byte for byte**. Active arms differ; all actor and critic weights and logs are finite.
- Actor-only evaluation smoke validates the existing 35-column episode logger.

See VALIDATED.json and validation/*.json for numerical errors, hashes and timings. The short tests measure correctness, not learning benefit or late-game throughput.

## Measurements and interpretation

Each final actor receives a fresh 512-agent evaluation, seed 7, 14,000 completed episodes. Discard the first 4,000; retain the next 10,000 through the established analyze.py. Training masks are retained and eval epsilon is zero. Auxiliary inference is disabled in eval. Report score, depth, BALROG depth/XP lookup and all 26 action-use rates. Eval episode ordering can shift slightly with completion scheduling; pairing refers to training initialization seeds, not exact matched trajectories after policies diverge.

`critic.jsonl` contains prequential residual moments per verb and sampled logit-gradient moments per head. Gradient moments exclude entropy, include the actual PPO clipping and IS correction, and sample every 64th training row. These are descriptive within-run diagnostics, not independent game-clustered confidence intervals; replayed observations repeat. `report.py` writes gradient_variance.csv and the final results table. No detector of successful item use is implied by action-use counts.

Screen at equal steps and report measured wall clock/SPS. Judge the four paired seed differences, not pooled episode uncertainty. A correction is worth confirming longer only if its variance reduction persists and item-use behavior/score show no clear regression; do not declare a win from a single seed. These runs do not establish behavior at 4B.

## Running and status

The queue is detached from the terminal, with a lock, explicit PID/start-tick records and a 15-minute no-output watchdog. Train/eval use one GPU sequentially. A failed training run retires that paired seed and appends a complete replacement triplet, preserving arm order; artifacts are never overwritten. After three training failures the queue stops for investigation. An evaluation may retry once. There is no silent checkpoint continuation.

`python /puffertank/experiments/nethack-q-baseline-20261007/status.py`

Artifacts: manifest.json (pinned code/config/engine hashes), events.jsonl, active.json, pending.json, logs/, runs/, checkpoints/. Auxiliary weights plus AdamW state are saved beside actor checkpoints as `.bin.aux`. No edits were made to the production checkout; the experiment is isolated under this directory. The original source commit is 3719caaaf945025e4e1e59c6556560d2ba9e3d1c; runtime engine is pinned by its SHA256, inherited from the validated linear-entity campaign. The linear-entity compile flag is **off** here.

## Budget correction

The initial 250M queue was stopped at the user’s correction, before any model finished. Its partial first control, logs and original manifest are retained in `superseded_250m/`. All 12 jobs restart from scratch with a 1B learning-rate and exploration schedule; no 250M checkpoint is resumed. The full queue is expected to take roughly 30–34 hours, so it will continue beyond the first overnight window.
