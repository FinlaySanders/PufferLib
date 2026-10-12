# Trainer realisation of the cache-affine rollout scheduler (experiment copy; trainer infra → handoff patch)

## What changes, in one paragraph
Today a rollout "buffer" is both the inference unit and the stepping unit: a fixed agent range whose forward launches when all its agents are
stepped, with the shared env pool stepping any ready game on any core. The new path (PUF_SCHED=1) decouples them. Stepping: every game has an
owner core; a core steps its own ready games, growing its active set only on demand, and borrows one tick of another core's ready game only when
none of its own is ready (replay harness: +11% at 350 us / +6% at 800 us over the pool at 2048 agents, 24 cores; pool stays below ~40 games/core).
Inference: S staging slots of R=128 rows each; a slot thread gathers up to R agents whose observations are ready (or whatever is ready when the
window = forward time expires), uploads them as one contiguous block, runs the existing per-buffer forward graph on the slot's rows, scatters the
outputs to (t_agent, agent) in the rollout buffer and the actions back to the agents, which become ready to step. Trajectory layout, learner,
batch assembly and async double-buffering are unchanged. Per-agent action sequences under a frozen policy are unchanged → BATCH_PROOF and
PUF_STATE_PROOF must be bit-identical to the pool path.

## Data and indices
- vec->observations/rewards/terminals/action_mask (host) stay per AGENT (the env writes its own rows). env->obs/rewards/terminals/action_mask
  (device) become per SLOT ROW: row r of slot s is agent idx[s][r] for this window. cpu_upload is replaced by a gather-upload: host memcpy of the
  R chosen agents' rows into pinned staging (R x (OBS_SIZE + mask + 8) ≈ 630 KB), one H2D per array, plus idx[s] (R ints) and t_of_row[s] (R ints).
- Recurrent state: today per buffer {L, apb, H} (buffer_states[buf]). New: one per-agent state {L, total_agents, H} (sched_state) plus the slot's
  buffer_states[s] used as staging: gather_state(idx) before the forward, scatter_state(idx) after. zero_term_state runs on the staged rows as now.
  initial_states snapshot: per staged row with t_of_row==0 (snapshot_state_idx), into init_slot(write_slot).
- Sampler RNG: today rng_states[buf][row]. New: per-agent sched_rng {total_agents}; gather/scatter the curandStatePhilox4_32_10_t around the
  sampler (64 B per row) so agent i always draws from stream i regardless of which slot/row forwards it.
- Rollout record: today record_rollout_step copies step_rollouts rows → rollouts[slot*H + t][start..start+B]. New record_step_scatter(dst, src,
  idx, t_of_row, R): row r → (write_slot*H + t_of_row[r], idx[r]); padded rows (idx == -1) skipped.
- Actions: sample writes env->actions[slot rows]; D2H of the R rows into pinned host staging; the slot thread scatters row r → vec->actions[idx[r]]
  and marks agent ready (push to its owner's ready ring).
- Padding: a window with n < R ready agents pads rows n..R-1 with idx=-1: obs rows zero, state rows pointed at a scratch agent slot; outputs ignored.
  Forward cost is batch-insensitive (0.29-0.39 ms for 128 vs 0.36 for 512), so padding is ~free.

## Host scheduler (src/env_sched.h)
Per agent: owner, t (steps done this segment), phase ∈ {PARKED (ready, not active this segment), ACTIVE_READY, STEPPING, INFER (obs pending/in flight)},
in a per-agent struct. Per worker: active count A_w, ready ring (SPSC-ish: producers = slot threads pushing agents whose actions came back; consumer
= owner; borrowers pop from the tail under the ring's spinlock). Global ready-for-inference MPMC ring (workers push after puf_step; slot threads
pop up to R). Worker loop (pinned one per physical core, as today):
 1. pop own ready agent whose phase is ACTIVE → step it (puf_step), t++, push to the inference ring (or mark DONE if t == H).
 2. else if an own PARKED agent exists → activate it (A_w++), step it. (lazy growth: the hot set grows only when nothing active is ready)
 3. else borrow: pop a ready agent from the busiest other worker's ring (any phase) → step it once; it stays owned by its owner.
 4. else spin (pause); never sleep (the harness showed sleeping cores lose 2-3%).
Segment = batch horizon H (the existing rollout): rollout_start(write_slot) sets t=0, phase=PARKED/INFER for all agents, arms the slot threads;
rollout_finish waits until done_count == total_agents (all agents reached t == H), then the learner runs on write_slot as today (async unchanged).
Tail: when a worker has no own agent left to step (all DONE or INFER), it borrows (step 3) — this is the harness's steal/split at single-game grain,
no separate mechanism needed. Ownership migration: optional, off (null in the harness).
Selection: PUF_SCHED=1 explicit; default rule for the handoff = agents per worker ≥ 40 → sched, else pool.

## Slot threads (replace vec_thread_main per buffer under PUF_SCHED)
loop while segment active: wait until inference ring has ≥ R agents or (ring non-empty and oldest entry older than window W = forward time) →
pop n ≤ R → gather rows → H2D (one memcpy per array, pinned) → gather_state/gather_rng(idx) → forward graph on slot rows (pufferl_forward with
PUF_REUSE_ROLLOUT graph per slot; nh_refresh_tables = true) → scatter_state/scatter_rng → record_step_scatter → D2H actions → scatter to agents,
push to owners' rings. Streams per slot as today (PUF_INFER_PRIORITY). W defaults to the measured forward time (EWMA of the last forwards).
Graph capture: the per-slot graph is captured once (t-independent, as PUF_REUSE_ROLLOUT already does); idx/t_of_row live in device buffers the
graph's kernels read, uploaded before each launch.

## Gates (in order)
1. Build sched_ctrl (unchanged source, new flags) — baseline binary, same source hash lineage as cohort_pin2.
2. Recorded-action replay (PUF_ACTION_REPLAY indexed by the agent's own t): BATCH_PROOF identical to the pool over 44 epochs at 2048/4 buffers.
   Replay under sched: action for agent i at its step t_i = file[stream(i)][t_i][i % 128].
3. PUF_STATE_PROOF identical (weights/optimizer state after N minibatches) → the rollout buffer (obs, values, logprobs, actions at (t, agent)) is
   bit-identical → gather/scatter, per-agent state and RNG are right.
4. Live obs-hash proof (new PUF_LIVE_PROOF: FNV over all agents' observations each epoch) identical to the pool under a frozen policy.
5. Fast protocol A/B (run_scale.py, 44 epochs from 32): 5M/2048 and 5M/4096, pool (cohort knobs, 24 pinned) vs sched; then 15M/2048; then 512.
