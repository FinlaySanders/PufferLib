---
name: nethack-cert-protocol
description: "How scores are certified — inline 10K eval after every train run (free, in .ini metrics), standalone eval needs burnin 4000; rolling finals are noisy not biased"
metadata: 
  node_type: memory
  type: project
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-14T15:24:57.659Z
---

Certification facts (established 2026-08-12, all cross-validated):

- **Every train run already ends with a 10K-episode eval** (`pufferl.cu` after
  the epoch loop: `eval_loop(EVAL_SCORE, base.eval_episodes=10000)`), and its
  score overwrites the FINAL curve point. It lands in the run's
  `logs/<env>/<run>.ini` `[metrics]` as the last `env/score` value (final
  `env/n` ≈ 10001+ proves it ran). READ THIS FIRST before running any eval.
- **Sweeps are fed that eval** as their last/highest-cost Protein observation;
  earlier curve points are rolling bin-means of the training log.
- The inline eval needs NO burn-in: it reuses the live training vec, so envs
  are mid-episode at random phases (no cold-start censoring).
- **Standalone re-evals** (`./puffer eval nethack base.load_model_path=...`)
  cold-start all envs simultaneously → first completions are length-censored
  short/low. Protocol: `base.burnin_games=4000 base.eval_agents=512`
  (eval_agents≠-1 also forces verb_eps=0). Burn-in logic was dropped in the
  5c cleanup and restored 2026-08-12 (eval_loop baseline-snapshot +
  `burnin_adjusted` stat dump; opt-in, fingerprint-safe).
- **End-of-training rolling `env/score` is NOISY, not biased** (window of a
  few hundred episodes, worth ±1000+; dswap1b_s704 rolled 13,689 vs eval
  8,861). Never compare configs on rolling finals; always use the 10K evals.
- Evals are NOT bit-reproducible (thread scheduling shifts the episode
  sample): same weights re-evaled spread ~±90-130 SE (full1b_s701: 9,394
  inline / 9,424 / 9,586 standalone).

**Why:** the morning-of-2026-08-12 cert fiasco: standalone evals without
burn-in read 1.4-6.9K low; the true evals were sitting in every .ini all
along. See [[nethack-epscore-median]] for per-episode dumps.
**How to apply:** for any completed run, read the .ini [metrics] final point
first; standalone re-certs always with burnin 4000 + eval_agents 512.
**2026-08-14: burnin STRIPPED from the branch** (in 58d36aaf nethack-challenge squash, user call, like
wandb; upstream's orphaned default.ini burnin_games=0 key kept —
default.ini is byte-identical to upstream) — the committed binary's standalone evals are cold-start
censored again (read 1.4-6.9K LOW, never trust them raw). For any standalone
re-cert: `git apply scratchpad/burnin.patch` + side binary, or rely on the
inline cert in the .ini (unaffected — needs no burnin by design).

**2026-08-25 matched-command hash rule**: ckpt-hash bit-repro comparisons
are valid only when the FULL train command matches — anneal_lr=1 makes
every ckpt depend on train.total_timesteps (66M-form repro can never match
a 1B run's 66M ckpt; this faked the retracted "lib era break", see
[[nethack-spell-channel]]). run_id and binary filename proven irrelevant
to ckpt bytes. Verified: v51b_s701 reproduces bit-exact (32M ckpt
8df9df83) on the post-rebuild lib with the matched 1B command.

**2026-08-26 5.0 confirmed: the inline cert IS recorded** — logs/nethack/<run>.ini [metrics]
env/score LAST point = the 10K inline eval (pufferl.cu overwrites scores[points-1] with
eval_loop result). Signature in stdout: Steps+Epoch freeze at final while score re-accumulates
over ~10 dashboards. Do NOT re-cert with bare `puffer eval` (no burnin/eval_agents → reads
low); the inline point is canonical. Earlier-session "rolling final" labels for gmp250/sc1b
runs were wrong — those are certs.

**2026-09-07 burn-in restored as a SIDE BUILD (97416d02 trainer has no burn-in; eval counts the first N completions -> standalone reads ~22% low vs inline):** patch = eval_loop warm-up until env/n >= base.burnin_games, then vec_log wipe, then the normal count (hand-off: scratchpad prof/handoff_eval_burnin.diff; also needs `burnin_games = 0` under [base] in default.ini). Built on vast as /workspace/PufferLib/puffer_burnin (sources restored; this box's CUDA 13 build won't load on the CUDA 12.8 boxes), copied to /workspace/sweeps/nh/puffer_burnin on the drone box. Usage: `./puffer_burnin eval <ckpt> --headless <trial args> --base.burnin_games=4000 --base.eval_agents=512 --base.eval_episodes=10000` (NETHACKDIR exported, burnin_games key present in the cwd config). First runs: t899/t781/t742/t865 1B ckpts + t973 dead ckpts (eval_burnin.log).
**BURN-IN VALIDATED (2026-09-07 10:00):** standalone headless evals with burnin_games=4000, eval_agents=512, 10K counted games reproduce the inline final evals: t899 1B 10535 (inline 10578), t781 1B 9060 (9097), t742 1B 11461 (11457), t865 1B 8888 (8887). Crashed-run checkpoints on the same protocol: t973 2B@1.44B 6625, t973 1B@524M 6555 (poor scaler, ~6.6K plateau). So 10578 and 11457 are certified in fresh processes; the earlier no-burn-in numbers (x1.28 correction) are superseded.

2026-09-07 13:00 t742 1B s201 STANDALONE CERT (local box, side build puffer_cert = release branch + handoff_eval_burnin.diff + per-episode dump hook prof/handoff_epdump.diff; NH_EPDUMP=path writes one line per episode: role race gend align how score max_depth steps turns max_xp exp gold ac hunger valid_moves illegal sells buys floors enhances floor_eats new_tiles min_ac + 26 verb_uses in NETHACK_VERB_STAT order): trainer score 11303.8 (10004 games after 4000 burn-in); per-episode window mean 11310, median 7496, p10 887, p90 26386, SE 122, sd 12175; depth 3.95, 30.8% reach dlvl5, 5.2% dlvl10; 25.3K turns/game. Per role: Barbarian 21.1K, Monk 18.2K, Valkyrie 17.1K ... Wizard 6.4K, Healer 4.9K, Tourist 3.3K (Healer/Tourist negative gold = shop buying). Race: dwarf 13.7K, orc 13.4K, human 11.7K, elf 9.1K, gnome 7.5K. Endings: killed 85.6%, poisoned 10.3%, starved 1.4%, GOD WRATH 1.3% (how_done=100 = NLE_HOW_WRATH, over-prayer: 17 prayers/game), stoned 1.2%. Verbs/game: search20 1394, runs 1344, throws 213, drops 149, engraves 108, eats 87, pickups 24, prayers 17, wears 15, casts 10 (Wizard-only 130). Analysis: scratchpad cert/analyze.py + make_report.py; the eval needs config/default.ini to carry burnin_games while running (ini parser rejects unknown CLI keys). Timing: full 14K-game cert ~12 min on this box (startup transient makes the first minutes look 10x slower).
