# cuBLAS patch: ten additional environment checks

Baseline: upstream/5.0 6ffa5b10. Candidate: candidate.patch, CUBLAS_DEFAULT_MATH, per-stream handles/workspaces. All runs serialized on RTX 4090. Seed 901, 32 training updates per run, upstream/candidate/candidate/upstream. Compare complete checkpoint SHA256 at updates 16 and 32, and verify every saved FP32 weight is finite. All 40 selected runs completed successfully, with 80 finite checkpoints. Production diff unchanged.

| Environment | Steps/run | Upstream repeats | Patch repeats | Patch matches upstream |
|---|---:|---|---|---|
| cartpole | 4,194,304 | Yes | Yes | Yes |
| pong | 2,097,152 | Yes | Yes | Yes |
| drone | 16,777,216 | Yes | Yes | Yes |
| tmaze | 4,194,304 | Yes | Yes | Yes |
| admiral | 16,777,216 | Yes | Yes | Yes |
| minimal | 16,777,216 | No | No | No |
| asteroids | 2,097,152 | No | No | No |
| snake | 4,194,304 | No | No | No |
| nmmo3 | 4,194,304 | Yes | Yes | No |
| craftax | 16,777,216 | No | Yes | No |

## Interpretation

- Five environments are repeatable and bit-identical across versions: CartPole, Pong, Drone, T-maze, GPU Admiral.
- Craftax is not repeatable upstream but is repeatable with the patch, similar to the previously tested NetHack outcome; no first-divergence investigation was performed for Craftax.
- Minimal, Asteroids and Snake are non-repeatable in both versions. This does not establish that their exact causes or amounts of variability are the same; causes remain unisolated.
- NMMO3 is repeatable in both versions, but checkpoint results differ. This is a concrete failure of universal upstream bitwise equivalence, even though patched repeatability passes. No long-run learning-quality conclusion is drawn.
- No tested repeatable upstream configuration became non-repeatable under the patch.

## Configurations and excluded attempts

Default model, rollout sizes, horizon and PPO settings retained. Total training duration shortened to 32 updates; checkpoint interval set to 16. Native default precision (BF16). Evaluation: 8 episodes; enough eval agents for the environment's agents-per-world and buffer count. Drone/Snake use 512 eval agents, NMMO3 4096, other selected checks 32. Craftax explicitly uses train.gpus=1; default requests 8 GPUs. GPU Admiral is built --cu, with selfplay disabled, num_policies=1, hist_policy_percent=0, selfplay.eval_games=0 to isolate ordinary training/evaluation. Other selected environments use CPU simulation.

Initial Drone/Snake/NMMO3 attempts completed training but failed evaluation because 32 eval agents were insufficient; superseded by successful reruns under corrected/. Initial Craftax attempted its default eight ranks on one GPU and failed allocation; superseded by the successful single-GPU test. Memory and Robot Arm fail builds identically on both versions (Memory header redeclarations; Robot Arm build-script obs_t detection); replaced by T-maze and GPU Admiral. These failures are not patch regressions and are excluded from the final ten.

## Artifacts

final-summary.json selects the definitive ten results. Initial source/ binaries and logs cover CartPole, Pong, Minimal and Asteroids. corrected/ covers the six remaining environments. results.json files contain exact commands, return codes, timings and checkpoint hashes. validate.py and corrected.py reproduce the protocol. Build logs for skipped environments retained.

Limits: one seed, short training, one GPU. This checks finite outputs, repeatability and checkpoint equality, not convergence, long-term score preservation or multi-GPU behavior. Previous CPU/GPU Breakout and 2048 checks are separate longer runs, all bit-identical to upstream.
