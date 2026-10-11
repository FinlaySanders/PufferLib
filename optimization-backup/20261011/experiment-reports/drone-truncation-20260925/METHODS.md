# Drone timeout bootstrapping experiment

Isolated source copy; production workspace remains unchanged. Nominal action centering is preserved. Training: 3 paired seeds 901/902/903 at DR=0.05 and 0.30, same current drone config and 89,150,896 requested steps (89,128,960 completed). 64 hidden units, two recurrent layers. Both experiment arms use the same rebuilt binary; PUF_TRUNC_BOOTSTRAP=1 enables timeout correction.

The environment records episode boundary, timeout-only flag, and final observation before automatic reset. Spatial failure takes precedence if simultaneous with a timeout. Both endings reset recurrent state and stop GAE propagation into the new episode.

For timeout only, evaluate V(final observation, old episode recurrent state) with rollout/actor weights. This uses copied recurrent state, consumes no action RNG and does not mutate live carry. Add gamma*V(final) to the transition reward used by GAE. The boundary flag remains set, so ordinary next-episode bootstrap is suppressed and the advantage trace stops. This is algebraically equivalent to separate termination and truncation masks with a final-state bootstrap. True terminals receive no correction. The GAE kernel itself is unchanged. Corrected reward is internal to training; logged environment reward remains unchanged.

Prototype scope: single-policy CPU drone env; not an upstream-ready general API. It performs an extra batched forward each step, even without timeouts, so its wall time is not a performance estimate for an optimized implementation.

Checks: real CUDA GAE unit check against scalar equations for continuing, terminal and truncated transitions; environment test verifies timeout/failure precedence and pre-reset observations; 2,097,152-step original/off/on runs produce bit-identical checkpoints before any timeouts. Tests are saved as selftest.inc, env_test.c and smoke.json.

Evaluation: original drone_nominal evaluator for BOTH arms, 512 agents, seed1701, 4,096 requested episodes, DR matching training. Compare per-seed metrics and the arithmetic mean across the three seeds; not an episode-pooled certificate. These are simulation tests only.
