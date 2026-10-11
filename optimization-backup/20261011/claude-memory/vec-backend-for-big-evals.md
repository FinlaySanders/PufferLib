---
name: vec-backend-for-big-evals
description: "Large episode counts (hundreds+) go through the vec/GPU backend (./puffer_<env> eval or train metrics), not the single-threaded CPU eval binary"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-09-03T18:51:12.155Z
---

When an eval needs many episodes (the user called 2000 on the CPU eval "way too many"), use the vec backend: `./puffer_<env> eval` / the trainer's metrics with thousands of agents. The `--cpu` standalone eval (src/puffercpu.c eval main, same path as the web build) is for small, instrumented looks: a few dozen episodes, per-death traces, exact-replay checks.

**Why:** the CPU eval is one thread and one env layout; the vec backend covers thousands of envs (and layouts) in seconds and is the number that matches training metrics.

**How to apply:** per-episode detail (positions, reasons) from a short CPU trace run; rates and aggregates from the vec backend. Related: [[nethack-cert-protocol]], [[supervised-probes-before-runs]].
