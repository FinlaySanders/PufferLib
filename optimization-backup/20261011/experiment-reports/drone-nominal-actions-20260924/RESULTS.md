# Nominal drone actuator mapping

Branch: drone-nominal-actions. Code changes remain uncommitted.

Action-to-RPM mapping and reset RPMs now use BASE_MASS, BASE_GRAVITY, BASE_K_THRUST and BASE_MAX_RPM. Randomised physics parameters remain in the dynamics. Renderer motor-command colouring uses the same mapping.

Compiled physics check confirms zero commands maintain nominal 14475.810 RPM independently of true mass, and otherwise identical light/heavy drones accelerate up/down respectively. Reset RPMs are independent of the randomised parameters. Build and git diff --check pass.

Training: existing config/drone.ini, seed 901, DR=0.05, one RTX 4090, 8 OMP threads. No changes to async/reset flags or hyperparameters. Completed 89,128,960 steps in 13.191 seconds reported training uptime, exit 0. Final weights finite.

Built-in final evaluation requested 1024 episodes with 512 agents. Final displayed metrics: perf 0.846; hover/perf 0.697; hover/ema_dist 0.026; race/perf 0.996; race/completed 0.991. These are built-in simulator metrics for one seed, not a hardware sim2real test.

Checkpoint: checkpoints/drone/nominal_s901/0000000089128960.bin. Command: command.json. Full log: train.log. Config snapshot: drone.ini. Source diff: change.patch.

Deployment must use the same nominal action mapping; existing real-flight deployment code was not inspected or modified in this task.
