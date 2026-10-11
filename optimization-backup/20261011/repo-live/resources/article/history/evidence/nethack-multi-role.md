---
name: nethack-multi-role
description: "Multi-role challenge protocol: 1B cert 6,608 beats AutoAscend mean +73%; engine role-order landmine (Rogue=7 before Ranger=8); audit CLEAN; mean-lever ledger from rich census"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-15T10:48:59.859Z
---

Multi-role campaign (2026-08-14). Protocol v2 = AutoAscend challenge: engine
PICK_RANDOM role/race/gender/align per reset, identity one-hots (13+5+2) in
extra at NETHACK_EXTRA_ROLEOH, align native in blstats[26]. Patches:
scratchpad/multi_role.patch (env), multi_audit.patch (env + NH_FEATAUDIT
hook). Binaries ./puffer_multi, ./puffer_multi_ev (census), ./puffer_multi_audit.

**Certified**: multi217_s305 = 3,718 (AA-mean parity); multi1b_s305 = 6,608
mean / 3,685 median — AutoAscend challenge mean 3,821 beaten +73%, median
5,337 still open. multi1b_s306 (flag binary, 2026-08-14) = 5,998 / depth
5.64 — seed pair mean 6,303, spread ±600 matches single-role basin noise;
flag path validated at 1B scale. 11/13 roles beat their 217M specialists at 1B (Priest 426%,
Ranger 121%, Rogue 104%; residual dilution Tourist 83% / Arc 82%). Curve
still climbing at 1B cutoff. multi2b_s307 (2026-08-15) = 5,889 FLAT — 2B adds
nothing over the 1B pair (6,303 ±600); budget lever exhausted, curve-still-climbing
read was basin noise.

**Identity-embedding A/B (2026-08-15)**: NH_ID_EMBED compile arm in nethack.cu
(#ifndef-guarded, default 0) — learned tables role 13×16 / race 5×8 / gend 2×8 /
align 3×8 (all numel%8), 40 dims appended to concat, one-hot bl features zeroed
under flag; indices from obs one-hots + al=clamp(1−blstats[26],0,2); zero-init;
deterministic batch-loop grad kernel; tables registered at END OF ENCODER
block (after spk2_b, BEFORE decoder+mingru — the overnight "last 288 floats"
tail probe was vacuous, mingru tail is always nonzero; real validation = FD
harness). Demo CPU mirror shipped in nethack.c under same guard (ide concat
tail + zeroed one-hots + ENC_FIXED +288; ./nethack_idemb side build loads
embed ckpts, float-count check 3,956,704 = onehot + 288 + 40*512). @217M ×5 seeds: one-hot mean 3,492 vs embed
3,756 (+264 ≈ 2.6σ, 4/5 B seeds beat A's best) — EMBEDDINGS WIN. Gradcheck
harness (tests/test_nethack_encoder.py) was STALE vs challenge layout (57
extras / 84*4 offsets hardcoded) — repaired to 77 extras + identity one-hots,
extended to the ide tables via NH_TEST_IDEMB=1 env (build -DNH_ID_EMBED=1;
tables randomized in-harness since zero-init hides forward bugs); both arms
PASS (FD ~1e-4 zero kinks, float64 torch ref ~1e-8). Confound noted: 40 direct
dims vs 20 bottlenecked-through-bl_hid — disambiguation arm = one-hots given
the same direct channel. **idemb1b_s311 CERT 7,035 / s312 6,929 (2026-08-15) = embedding pair mean
6,982, NEW multi-role RECORD** — both seeds beat both one-hot 1B seeds
(6,608/5,998, mean 6,303), +679 pair-mean; clean 2/2 separation seals the
embed win at 1B. Built with puffer_idembw (wandb.patch + define-flip side
build). **COMMITTED 7f6ec43b 'embed' 2026-08-15**: NH_ID_EMBED default 1
(train), demo runtime-adaptive (infers ide from float count — one binary loads
both eras; score→ide=1, depth→ide=0), resources score weights = s311 ckpt,
tests pass -DNH_ID_EMBED explicitly (A arm needs =0 now). NEW ERA FPRINT
486f55e1aa5d... (2M seed 777) = bit-identical to the A/B's puffer_idemb gate
smoke; old one-hot default era ref 48b48c48... now needs -DNH_ID_EMBED=0.

**LANDMINE — engine index orders** (verified in role.c + census race-validity):
roles = Arc0 Bar1 Cav2 Hea3 Kni4 Mon5 Pri6 **Rog7 Ran8** Sam9 Tou10 Val11
Wiz12 (Rogue BEFORE Ranger); races = hum0 elf1 dwa2 gno3 orc4; align = law0
neu1 cha2. I originally swapped Rog/Ran in every census table (caught by the
2026-08-14 audit; artifact corrected). "Elf Rogue" cells are impossible —
Rogues allow hum/orc only; Rangers allow hum/elf/gno/orc.

**Audit 2026-08-14 CLEAN** (NH_FEATAUDIT on multi1b, 10K-ep eval, 26.2M
packs): identity one-hots vs nle_identity vs welcome-message text = 10,039
checks 0 mismatches; one-hot/align integrity 0 violations; liveness constants
all benign (invcnt RANDOM/ILLOBJ/CHAIN/VENOM + spell slots 5-8 never filled).
Welcome-parse gotchas: gender adj printed only for dual-gender roles without
a female name variant; Valkyrie female-only; Priestess contains "Priest".

**Mean-lever ledger** (multi1b rich census n=8,008, mean 6,021 sample):
- Weak roles are RATE-limited, not lifespan-limited: score/1K-turns Tou 197,
  Hea 236, Rog 263, Pri 269, Ran 295 vs Mon 733; lifespans all 10-17K turns.
  Bottom-6 roles contribute 1,848 of 6,021 → sampling-curriculum pool ≈ +1.5K.
- Fainting-fix prize REFUTED at 1B: hungry-vs-fed death score delta nets
  +120 mixture mean (dying hungry is the natural end of successful farms).
- Poison deaths (9.1%, mean 7,931, kml=0, orc rate ≈ non-orc) are FOOD
  ILLNESS (rotten-corpse Sick, resistance doesn't help) — the corpse-rot
  lottery taxing the best farmers. Stoning 0.7% at mean 18,743 (25/55 Monk
  = martial-arts vs cockatrice) kills the very best runs.
- Arc dig-and-cash: 13,194 score/1K turns (highest rate in game), dies ~470
  turns at xp 1; elb-high tercile lives 3x longer and scores 3x (5,768 vs
  1,927) — Elbereth-protected digging is the extension gradient.
- minac within-role terciles: +1.5K..+9.7K every role (confounded but huge);
  armor consistency = strongest cross-cutting lever (ac_coef=1.0 arm).
- Weak-role forensics (2026-08-15 rerun of the rich census): weak roles die
  92% to monsters at killer-mlev 1.8 (trivial threats) vs strong 83% @2.9;
  bot-tercile signature = 3-6K turn deaths with wear 3-10 / minac 5.6-7.6 vs
  top-tercile wear 22-30 / minac 1.9-3.5 → armor onboarding is THE within-role
  separator. Pri/Hea cast ≈ 0.0/1K vs Wiz 13.6 — class mechanic dead for the
  two roles that need it most. Depth ceiling: even TOP-tercile weak roles stay
  at ~2.8 avg depth while strong roles farm 4.5-5.0; s20 rate ~50-72/1K across
  all roles = one strategy copy-pasted role-agnostically, conversion differs.
  Tourists DO throw (23.6/1K, highest). Dump now has gold col 27 (prev_gold,
  teardown-safe; patch regenerated 2026-08-15; dump writes ONE file at the
  NH_EPS_DUMP path — no e.* glob).
- s311 embed census (n=7,840, same 8K protocol): mean 6,794 / median 4,510 vs
  one-hot census 6,045/3,926 — AA-median gap narrowed 1,411→827. Gains broad
  (10/13 roles up): Arc +3,157 (ABANDONED the 0.5K-turn suicide-dig for
  19.8K-turn farming, depth 20→5, wear 0.3→13 — biggest single strategy flip),
  Kni +1,082, Ran +1,035, Rog +927, Sam +781, Tou +643. Priest CAST UNLOCKED
  0.0→3.1/1K (predicted differentiation test passed); Healer still dead (0.7,
  score flat −24). Macro strategy spread UNCHANGED (depth std 1.04→1.01, s20
  std ~6.2) — same farm loop, better per-role conversion; weak-role churn
  down (wear 15.9→12.3 with minac 4.6→4.2, die<6K 25%→22%). GOLD = 0.6% of
  score both embed seeds — kills+depth are the whole engine; gold/shop levers
  dead for score.
- HEALER PROBE (2026-08-15): healer200m_s313 (role:Healer forced in rc via
  puffer_healw side build, embed arm) cert 1,423, casts 0.73/ep trace, eps die
  ~1.4K steps — vs budget-matched one-hot 217M multi Healer 1,202 (med 837)
  and 1B multi Healer 2,502-2,685. Specialist +221 only at matched budget
  despite 13x the Healer steps → interference is NOT Healer's problem; multi
  transfer carries the role, casting never emerges solo either. Wall =
  bootstrap learnability (weak combat → short lives → farm loop never starts).
  healft_s314 = warm-start fine-tune from s311 + Healer-only 200M, running.
  Next if flat: CAST/healing mask interaction (is a beneficial heal ever
  experienced? full-HP casts waste; check legality gating vs hp_frac).
- s312 census REPLICATION (n=7,958, mean 6,618 / med 4,564): Arc flip
  replicates (18.2K turns / depth 5.5 / wear 15.5 — config-level fact), Pri
  cast replicates (3.9/1K), Hea cast dead BOTH seeds (0.1-0.7 trace, the one
  stuck role), weak-role median up both (2,762/2,906 vs 2,420). Sam/Ran/Rog
  per-role gains were partly seed-specific (Sam +781 s311 / −322 s312);
  consistent both-seed gainers = Mon Bar Kni Arc Pri Tou. Embed census
  medians 4,510/4,564 vs AA 5,337 → gap ~800.
- 100K cap: 0 hits at multi (max time p90 ~37K) — cap not binding.
- Census how=100 rows (2.3%) = my dump's truncation marker (eval-boundary
  flush), NOT deaths; engine panic path uses PANICKED=11.

**Flag COMMITTED 2026-08-14, squashed into 58d36aaf 'nethack challenge'** (+71/−7, telemetry kept
out per user; eps-dump lives in scratchpad/eps_dump.patch): `env.multi_role` ini flag
(default 0) replaces the puffer_multi side-binary; identity one-hots are now
ALWAYS in the obs (fixed character when 0 — role_ix 5.000 vs 5.965 smoke).
LANDMINE: obs grew +80B (57→77 extras) so pre-flag single-role checkpoints
(new1b_s305 12,864 line) do NOT load in the new binary — rebuild from tag pre-challenge-squash ancestry:
0487323e to eval them; multi checkpoints load fine. New fpgate era ref
48b48c482ece8e674b60496e711f1b2ba2ef4054aed587711f2ee4d74fd17620 (prev
703c4adf...). Vendor side PUSHED 2026-08-14: fork main 03e0b034d (post-death
UAF + stale-returncontext crash fixes) + 31f1583cd (nle_identity export) —
the ocean flag diff builds against fork HEAD now. Neutrality of the 20 constant features on
single-role training unverified — run one 217M default seed before trusting
the new binary for champion-line work.

**Why:** the label swap shipped into an artifact; index assumptions must be
verified against the engine table, not memory of NetHack docs.
**How to apply:** any per-role analysis of census files must use the order
above; re-run NH_FEATAUDIT (multi_audit.patch) after any obs change; census evals =
apply scratchpad/eps_dump.patch (user keeps telemetry out of the tree) +
build a side binary + NH_EPS_DUMP=<path> (+ pthread.h include rides in it); next
levers in order: idemb at 1B (running), embedding-vs-channel disambiguation arm,
multi hyper-sweep on box, ac_coef multi arm, role-sampling curriculum (2B budget
DEAD). See [[nethack-env-setup]], [[nethack-cert-protocol]],
[[nethack-tempo-hygiene]].
