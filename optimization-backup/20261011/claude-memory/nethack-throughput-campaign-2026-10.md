---
name: nethack-throughput-campaign-2026-10
description: Oct 2026 throughput work - regime ablation grid (15M/5M x 512/1024/2048/4096), fast protocol, phase-aware GPU config, minibatch, fused Muon; only cuBLAS fix committed; harness + results in experiments/nethack-24h-20261009
metadata:
  type: project
---

State as of 2026-10-10 ~12:30 UTC. Codex 24h campaign (NETHACK_OPTIMIZATION_REPORT.md, untracked) consolidated; my regime grid built on its harness.

Harness: /puffertank/experiments/nethack-24h-20261009: campaign_ablate.py (resumable, continue-on-error, runners primary/model/scale), make_ablate_specs.py (FULL stack env + arms()), run_scale.py (--agents/--horizon/--minibatch at constant batch), summarize_ablate.py <tag>. Results ablate_*.results.json. Binary binaries/attribution_v37 (experimental stack, all toggles via env). Engine levels via LD_LIBRARY_PATH: stock=vendor/fast-nle/build, sept14=nethack-perf-20260917/tight-loop/campaign2h/final, precompact=nethack-locality-target-20261008/engines/persist/build, retained=nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/build.

FAST PROTOCOL (certified vs long window, 15M/512: identical full-stack SPS, GPU arms within 0.2pp, CPU arms ~2pp pessimistic): 512 agents --epochs=28 --start=16 (~36 s/run), 2048 agents --epochs=44 --start=32 (~56 s/run). Never run GPU timing concurrently; nice -n 19 any side analysis.

FINDINGS: two phases. GPU-bound only at 15M/512 (PPO 1133 ms, rollouts 215 ms early). Everything else collection-bound (5M/512 GPU idle 35%, 5M/2048 idle 55%). Engine ladder pays everywhere: 1.75x (15M/512), 2.1x (5M/512), 1.57x (2048); compact-state step +7/+18/+19/+29% growing with collection-boundness; obs hashes identical at all engine levels. GPU kernels (fast kernels 9%, lanes 9%, entity 3.5%) matter only at 15M/512. Scaling at constant batch: collection cost +17% (512->1024), +9% (1024->2048), flat to 4096. PPO phase ~10% longer at H512 than H128 (recurrent scan parallelism). Phase-aware config: collection-bound -> gradient overlap OFF (+1.5-2.4%) and lanes 1 (+0.7%); GPU-bound -> overlap on + 32 connections + 4 lanes. NEVER overlap on with CUDA default 8 connections: -27%/-41% (event waits in dW stream block aliased inference queue). Fused small Muon (PUF_MUON_FUSED_SMALL=64, 21 matrices) +1.85% at 15M/512 (campaign parked it at +0.08% measured at 2048 = wrong regime); numerics not bitwise. Minibatch at 15M/512: 8192 +11.3% (best), 16384 +8.4%, 32768 +6.9% - PPO shrinks 1135->780 ms but collection slows 917->1040 ms (long kernels raise inference latency); at collection-bound regimes 32K is +1.4% (15M/2048) or -3.1% (5M/512). Inference call: 13 launches, 45 us kernels, 546 us span under PPO; collectors wait 41% of cycle at 512 agents.

**Why:** the sweep goal needs a throughput floor across regimes; collection (engine + inference latency) sets it.
**How to apply:** gate GPU candidates at 15M/512 and CPU candidates at 2048/5M; quote regime with every number; see [[nethack-engine-scaling-program]] for next steps; [[pufferl-off-limits]] still applies (patch + hand off).
