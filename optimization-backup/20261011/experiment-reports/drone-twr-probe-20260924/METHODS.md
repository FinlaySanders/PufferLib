# Drone thrust-to-weight probe

Target: maximum thrust / weight = 4*k_thrust*BASE_MAX_RPM^2/(mass*gravity). This is actuator authority, not instantaneous commanded thrust/weight. Gravity remains randomized by +/-1%; the DR setting independently randomizes mass, thrust coefficient, inertia, motor time constant and other physics parameters by +/-DR. Action centering uses nominal parameters throughout.

Three training seeds (901, 902, 903) at each of DR=0.05, 0.15, 0.30. Every policy receives the same ~89.13M-step training budget and architecture (64 hidden units, 2 MinGRU layers). Existing nominal-action 5% checkpoints are reused; 15% and 30% policies are freshly trained with only DR changed. models.json records checkpoint hashes and new training commands.

Frozen FP32 CPU deployment policy with deterministic mean actions. Each policy is evaluated at its training DR and at a common DR=0.30. Each evaluation samples 4,096 fresh drones, half hover and half race, for up to 5 seconds. Labels are diagnostic only and are never fed to the policy. No policy training takes place during collection. Recurrent state starts at zero for every drone. Rows are recorded at 0, 0.1, 0.5, 1, 2 and 5 seconds, after processing that time's observation. Once an episode terminates, later rows for that drone are excluded rather than replaced by a new episode.

Features: 23 current observations, 128 recurrent carry values (both layers), or 64 final policy-output features. Binary records are 220 float32 values: episode id, step, task, target, distance, observations, state, output.

Held-out split by entire drone/episode: 2,458 train, 819 validation, 819 test, fixed permutation seed704, shared across all models and times. Ridge regularisation is chosen on validation data, with training-only standardisation. Nonlinear readouts are histogram gradient-boosted trees (150 iterations, 7 or 15 leaves selected on validation) at 5 seconds; also fitted separately by task. Report R2 and MAE on the untouched test split. No overlapping frames from a test episode are in probe training. Policy seeds are summarized separately then averaged; they are not pooled into one probe.

Interpretation: readout success shows accessible information, not a causal demonstration that control uses an explicit physical parameter estimate. Low linear R2 does not establish absence. DR comparisons need the common test distribution: wider targets and stronger motion signals can improve decoding even without retraining. This is a small controlled experiment, not a hardware sim2real validation.
