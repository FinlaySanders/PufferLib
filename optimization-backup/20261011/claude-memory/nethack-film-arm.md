---
name: nethack-film-arm
description: FiLM arm (NH_FILM) built+gradchecked 2026-08-15 — identity embeds scale/shift the encoder output; night-queue panel film_s401-405; plus the trap-wiped-code and concurrent-fpgate landmines
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-15T22:20:08.229Z
---

**NH_FILM** (ifndef 0 in nethack.cu, requires NH_ID_EMBED): after the proj
relu, out' = pre * (1 + ide·Wg) + ide·Wb, ide = the 40-dim identity tail
already in the concat (NH_IDE_CONCAT_OFF), Wg/Wb (40, hidden) zero-init so the
arm starts as the exact baseline. Encoder-side only — the MinGRU trunk is
untouched (user rule: no trunk changes). Kernels: nh_film (fwd),
nh_film_wgrad (per (k,h), batch loop, deterministic), nh_film_dide (per-sample
grad into the identity vector, added by nh_idemb_grad_kernel via a new
film_dide arg — NULL when off), nh_film_dpre (grad *= 1+gamma in place, last
reader), relu bwd then masks against film_pre not out. Gradcheck PASS (FD +
float64 torch, ide tables re-checked with the extra path). Flag-off tree
fingerprint UNCHANGED 486f55e1. Patch: scratchpad/film.patch (279 lines);
harness support: NH_TEST_FILM=1 (needs NH_TEST_IDEMB=1), randomises the
zero-init tables (glb1_xy idiom); tests/ diff in
scratchpad/harness_widths_film.patch — the harness now derives ALL widths
(D, LOC, P1, GLB, INV, POOL, BL, SPKEY) from the built lib's numels, so any
width arm gradchecks without edits (spell query sliced to :SK).

**Why:** identity embeds (+264, the only proven 5-seed win) were pure input
concat; FiLM lets role change the computation. Night-queue rank 3.

**Landmines hit building it (2026-08-15 night):**
1. `trap cleanup EXIT` with `git checkout -- ocean/nethack/` WIPES UNCOMMITTED
   NEW CODE — the FiLM code vanished after its gradcheck shell exited, the next
   shell's `sed NH_FILM 0->1` matched nothing, and I built a PLAIN BASELINE
   binary named puffer_filmw (caught only by grep -c NH_FILM == 0 and md5 vs
   baseline). Rule: `git diff > scratchpad/X.patch` IMMEDIATELY after writing
   new code, before any shell that traps; sanity-check arm binaries by size /
   `strings | grep -c <new symbol>` before handing them to a queue.
2. fpgate concurrent with a live training run: arm 1 passed, arm 2 aborted in
   cudaGraphLaunch (GPU contention). The training run survived. Don't run the
   gate alongside training; one arm's PASS is what the flag-off check needs.
See [[nethack-multi-role]], [[nethack-launcher-gap]], [[nethack-env-setup]].
