# Rollout attribution, 2026-10-10

Question: after fusion and scheduling changes, is exposed rollout wait CPU-limited?

Use the existing 15.55M frozen score actor, exact recorded actions, 2048 environments, 4 buffers, horizon 128, minibatch 4096, 113 updates per epoch in full runs. All arms warm through 64 epochs with full training computation. Change only diagnostic work at epoch 64; compare mature epochs 64-78. Baseline engine remains retained movement_object_presence_pgo_followthrough.

Run a low-overhead graph-level Nsight trace with CPU NVTX ranges. Compare unprofiled controls and run:
- Full training, 32 workers (bracketed control).
- Same rollouts with concurrent PPO disabled: removes GPU training contention plus host training work.
- Same environment/action replay with PPO and inference disabled: retains action copies and observation uploads. This is a diagnostic engine-plus-transfer ceiling, NOT a training speedup.
- Full training at 24 and 16 workers: CPU resource sensitivity.
- Isolated GPU training of the saved mature batch, for a complementary ceiling.

No-inference mode requires no-training, frozen actor and saved actions. It leaves recurrent/rollout tensors stale after epoch 64; they are not used for training. Every environment observation hash must match across all arms, and actor checkpoint hashes must be unchanged. BATCH_PERF's updates field is configured updates, not executed updates in no-training arms; report actual executed updates as zero.

Profiler times, stage sums, counterfactual rates, and training throughput must be distinguished. Do not add overlapping stage durations. Keep builds and measurements serialized. No changes to production sources/defaults.

Follow-up diagnostic control: /proc sampling shows no-PPO main thread burns ~0.96 logical core waiting for rollouts. Repeat full, no-PPO, and no-PPO/no-inference with existing PUF_FINISH_SLEEP=1 (condition-variable main wait) to avoid replacing removed GPU work with an extra CPU spinner. These are diagnostic controls, not a proposed new optimization. GPU SM clock drops from2715 to~2520MHz when PPO is removed; record this as a DVFS confound. No global clocks changed.
