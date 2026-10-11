---
name: nethack-optimization-backup
description: Where the NetHack speed work is backed up (branch backup/nethack-optimizations-20261008 in both repos, worktrees under /puffertank/optimization-backup-20261008, preserve scripts) and what each dated directory holds
metadata:
  type: project
---

Backup branch `backup/nethack-optimizations-20261008` exists in BOTH repos (FinlaySanders/pufferlib remote `origin`, FinlaySanders/fast-nle `origin`),
checked out as worktrees in /puffertank/optimization-backup-20261008/{pufferlib,fast-nle}; the live checkouts (/puffertank/pufferlib on
drone-nominal-actions, vendor/fast-nle on nle-stock) are never modified by the backup.
- 2026-10-08: `optimization-backup/20261008/` (preserve.py): env pool, sampler, gemm, parked work; fast-nle got a 17-file engine change in-tree.
- 2026-10-11: `optimization-backup/20261011/` (preserve_20261011.py mt7|dv4|docs): fast-nle tip 3f671b8d3 = mt7 stack in-tree (fffb750c2) + dv4
  (c82fb949f) + engine ledgers; pufferlib b3aa85cc = cohort patches, trainer-cohort/overlay (full experiment trainer), engine-scaling docs,
  harness-24h (+ source-src). PUSH_VERIFIED_20261011.json records local == remote.

**Why:** box maintenance; experiments/ is not under git (72 GB of runs stay on /puffertank only).
**How to apply:** to add a new day, copy preserve_20261011.py, change PREFIX/date, stage per repo, commit with plain messages, push, verify
local==remote. Pushing from this shell works (gh helper warnings are harmless). Run the `docs` stage last; `engine_intree` overlays an
engines/<name>/source tree (skips *.orig, .git, optimization-backup).

2026-10-11 host-disk copy: /puffertank/docker/nethack-backup-20261011/ (= host ~/puffertank/nethack-backup-20261011; the only path that is NOT the
container overlay — /root and /puffertank/experiments are container-local): claude/ (memory + all session transcripts gzipped), oracles/ (actions
corpus 1.3 GB, goldens, fuzz, final_hash_opt61 reference hashes, gates, dat), engines/ (mt7, dv4 source + PGO libs), backup-tooling/. 1.7 GB total.
Not backed up anywhere: experiments run directories (72 GB) and trainer binaries — results are in the git backup, binaries rebuild from overlays.
Full inventory 2026-10-11 (host dir): + repo-worktrees/ (every worktree's diff + untracked tarballs; pufferlib-5c 7919bbda is the ONLY commit on no
remote → bundle), experiments-docs/ (all 111 campaign dirs' documents), misc/ (5c-checkpoints, sweep2_top_checkpoints, spell-cast-patches,
backups, constellation_nethack, auxdata, box_archive, drone-backup-20260914). Skipped: declab 9.5 GB dumps, venvs, 72 GB of runs.
Everything under /puffertank except /puffertank/docker is the container overlay.
+ misc/mask-campaigns/ (2026-10-11): nethack-mask-ablations-20260929 (27 runs, 1B, individual mask removals), nethack-mask-combined-20261002 (7 runs,
all three removed), nethack-nearby-pass-20261002 (5 runs), nethack-zt-mask-eval/replication-20261006, nethack-nearby-probe-20261003 — runs/, validation/,
RESULTS.md and the FINAL checkpoint per run (intermediate checkpoints dropped: 13.4 GB → 1.9 GB). Results: every mask removal is within seed noise of
baseline (means 12.4K-14.8K vs baseline 13.2K-13.4K); only RUN/SEARCH20 removal (4.9K) and verb-epsilon removal (9.3K) collapse; zero-time mask
costs ~7% score at the stock backend but removes all clockless timeouts. Full tables in NETHACK_ABLATIONS.md (repo root) + the campaign RESULTS.md.
2026-10-11 f355acbb (pufferlib backup branch): optimization-backup/20261011/mask-ablations/MASK_ABLATIONS_RESULTS.md = consolidated mask/passthrough/
zero-time results + each campaign's RESULTS.md, manifest, validation, per-run results.json + the 29 Sep audit. Load-bearing: RUN/SEARCH20, verb epsilon.
Removable (noise at 1B): handless belief, hostile-ray preference, strategic item masks, nearby-entity passthroughs.
