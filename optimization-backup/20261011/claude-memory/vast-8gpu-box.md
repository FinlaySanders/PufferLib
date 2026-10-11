---
name: vast-8gpu-box
description: Vast.ai 8x4090 training box (instance 49574713) reached from this box as `ssh vast`; paths, toolchain, landmines, driver
metadata:
  type: reference
---

Vast.ai instance 49574713: 8x RTX 4090, EPYC 7A13 (256 threads), 503GB RAM, 256GB disk, Ubuntu 24.04, CUDA 12.8 toolkit (driver 610 supports 13.3), image vastai/base-image_cuda-12.8.1. SSH: `ssh vast` (config on puffertank: 8.17.147.152 port 41439, key ~/.ssh/id_ed25519 "puffertank-control"). Repo at /workspace/pufferlib with /puffertank -> /workspace symlink (same absolute paths as here). Python: /venv/main (numpy, wandb; torch installed 2026-09-01). Set up 2026-09-01: full tree transferred (tar pipe), ./puffer built on CUDA 12.8 (arch native=sm_89), goldens 34/34 PASS, GPU smoke clean. wandb_tail.py must be copied to scripts/ on the box (it lives in the puffertank scratchpad, not the repo) — fixed 2026-09-01 23:20 after 8 silent tailer failures. Per-GPU driver: scripts/vast_panel.sh <bin> <prefix> <steps> gpu:seed...; status in /tmp/<prefix>.status.

**Landmines**: the Vast login shell prints a banner on every ssh -> rsync protocol breaks ("shell not clean") — use `tar cz | ssh vast 'tar xz -C ...'` for local->box; for box->local the banner lands IN the stream: `ssh vast 'tar cz ...' | python3 -c "cut at first b\x1f\x8b" | tar xz` (tail -n +N is fragile). ssh commands start in /root — always `cd /workspace/pufferlib`. Piping build output through `head` SIGPIPE-kills build.sh (set -e) — log to a file instead. Unprivileged container: no perf/eBPF/sysctl/docker; long services via supervisor per /etc/vast-agents-guide.md.

**Why:** control plane stays on the puffertank session (memory/labs/checkpoints here); the box is a training farm — 8 seeds in parallel = a full n=5 panel + spares every ~2h. **How to apply:** launch panels with vast_panel.sh over ssh, pull certs/logs back with tar pipe; keep GPU-touching validation off the puffertank GPU while its panel runs.

2026-09-07 17:40: vast box idle after sweep #2; top-3 sweep checkpoints saved locally at /puffertank/sweep2_top_checkpoints/ (t1190 289M 74.8 MB = 1024x5, t1122 210M, t0973 333M); all 1200 sweep inis in scratchpad const_nh + /puffertank/constellation_nethack/data. User asked whether the vast box can be killed -> yes, nothing left there we need (burn-in side build also exists on the drone box).
