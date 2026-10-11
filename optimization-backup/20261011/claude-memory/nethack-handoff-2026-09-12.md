---
name: nethack-handoff-2026-09-12
description: "Live queue and decision rules as of Sat 2026-09-12 20:15 — what is running on each box, where each result lands, and what to do with it (article due Mon 09-14)"
metadata: 
  node_type: memory
  type: project
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-09-12T15:19:33.849Z
---

State docs (authoritative, all committed on `nle-stock`, pushed): `scripts/nle_stock/LEDGER.md` (numbers), `STATUS.md` (narrative),
`ARTICLE_PLAN.md` (article structure, timeline, bug table, weekend schedule). Read those first; this note is only the live queue.

**Headline (16:20):** 1B ladder closed at every rung: fork 13,060 / 8,618, stock strict 12,785 / 8,522, Python rung 4 12,900 / 8,389 (480 games).
**2B `claim2b_s503`: stock −13 % on two seeds** (14,357 / 8,398 s21, 14,816 / 8,856 s32 vs fork 16,520 / 9,839 s21, 17,159 / 10,112 s7), 0 aborts; loss in
weapon roles (Valkyrie −27 %, Barbarian −26 %, Caveman −24 %), casters/Monk at parity. Guard-off arm −7 % with aborts → guard stays.
**Lead hypothesis: the weight channel.** The fork's `nle_weight` exports the TRUE-type weight of unidentified boots/gloves/helmets/gray stones; NLE hides
types in every glyph (`winrl.cc shuffled_glyph`), so it is not derivable — 5.5 % of stock steps carry a wrong weight (`NH_STOCK_WTCHECK`), only in
roles that pick up armour. Identity bug fixed (`5ee2c435`: the 80-column welcome line carries a `\n` at the tty wrap; 1 % of games were male humans).
Binaries: local stock 452e91f52153 (5ee2c435), libnhagent bf00d5903920; drone stock 52336c7a6585 (3b44bca3, adds NH_STOCK_WTREAL crutch).

**Local (4090) queue — results append to `/tmp/reg/log`:**
- `claim2b_noguard_s21` → lands ≈ 16:30; interim −7 % vs guard-on, 63 aborts (guard stays).
- `canary3_2b_s21` (derive v3, default masks, seed 21, 6,000; started 16:01, ≈ 17:20) → compare to 14,357 / 8,398 (v1) and fork 16,520 / 9,839.
  Expect a small change (identity 1 % of games + hallucination hold). Not the decision point any more; the weight tests are.
- `claim2b_nomask_s21` (NH_NO_CANT_HOLD=1, derive v3; started 16:14) → vs canary3: form mask cost/pay on stock.
- `claim2b_fakeclock_s21` (canary3 config minus NH_STOCK_REALCLOCK → backend's seeded fake date; waiter gated on canary3's bash pid 2052617) →
  **canary3 minus this = today's NEW-MOON calendar cost** (cockatrice hiss stones every time on a new moon; stock melee roles stoned 6–10 % of games
  vs 2–4 % on the fork). Sep 12–14 new moon: every stock number this weekend carries it; quote real-clock numbers with the date.
- Scripts `/tmp/reg/*.sh`; analyzers `scripts/nle_stock/box/analyze.py`, `box/ep_census.py`, `gym_analyze.py`.

**Drone queue — results in `/workspace/sweeps/certq/equiv/equiv.log` and `/workspace/sweeps/nh/long.log`:**
- `DONE stock_wtreal_s21` (gpu 7, ≈ 18:00): stock strict 2B seed 21 6,000 with the ENGINE's weight/capacity fed to the policy (diagnostic crutch, never a
  cert). **vs canary3_2b_s21 (same tree/seed) = the weight channel's cost on stock.** If it recovers most of the −13 %: fork-side export bug, fix =
  appearance-canonical weight export + retrain (not before Monday; claim carries it as a residual). If not: next suspects intrinsics (missed messages),
  hero_tile/food_underfoot, then the form mask arm.
- `DONE hw_real0_s21` / `DONE hw_wder_s21` (gpu 0, ≈ 17:00): fork harness all-real vs weight-derived-only, same seed; the harness regime is degraded
  (mode 0 itself −37 % vs the fork), so read the pair only relative to each other.
- 4B lanes `nlestock4b_s601–604` land ~19:30–21:00, `nomask_s607/608` ~03:00–05:30 Sunday (`DONE nlestock4b_...` lines with `last_ckpt`).
  Sunday morning: rung-1 fork certs of all six (`box_equiv.sh` with `R1=1 R3=0 R4=0`, LANE=<lane>, 14,000 eps; weights under
  `/workspace/sweeps/nh/checkpoints/nethack/<lane>/`), pick the best two by fork cert, then rung 3 strict (seeds 21/32, derive v2) and
  rung 4 python (2,000 games if time) for the best. Every cert now carries census columns (role race gender max_depth last_turn killer).
- Do NOT run harness `derived`/`real0`/`keep_*` score arms: not stock proxies (−48 % / −37 % vs stock's −11 %). Mode-0 recordings for the bench are fine.

**Rules that bit today:** verify kills by pid re-list; never gate a waiter on a log line that may already exist (gate on a pid or on lines after the current count);
two 512-agent stock evals fit the 4090 (11.9 GB each), a third does not; `${VAR:-x}` treats an explicitly empty VAR as unset; ssh to vast boxes needs `</dev/null`.
Moon phase: Sep 12–14 new moon; Sep 26–28 full moon (+1 Luck); Nov 13 2026 Friday 13th (−1 Luck, and the identity line displacement).

**17:45 — WEIGHT LEAK FIXED IN THE FORK, LEAK-FIXED LANES QUEUED (user: "get a fixed version training asap", 2×1B, 2×2B, 2×4B).**
Fork `f7d8749ab` (fast-nle nle-stock): `nle_weight` prices by true type only while the name is displayed, else the appearance's canonical slot (via
`nle_shuffled_glyph_c`); dead corpse-age hooks removed. Hooks are not in the golden hash → gate unchanged. ENGINE.txt pin updated (pufferlib 5.x on nle-stock).
Drone: separate tree `/workspace/pufferlib_fix` (never rebuild `/workspace/pufferlib`'s libnethack.so while its six trainers run). Build log
`/workspace/sweeps/nh/fixbuild.log` (DONE marker gates the lanes). Driver `/workspace/sweeps/nh_fixwt.sh`, cwd `/workspace/sweeps/nhfix`
(checkpoints/nethack/<lane>/, panel_<lane>.out), queue longest-first: fixwt4b_s705/706 (4e9), fixwt2b_s703/704 (2e9), fixwt1b_s701/702 (1e9);
one worker per GPU 0/1/2/3/5/7, starts when idle; START/DONE lines in `/workspace/sweeps/nh/long.log` (tag FIXWT). GPUs 4/6 = nomask leaky 4B lanes (keep).
Expected landings: 4B ≈ +20 h, 2B ≈ +10 h, 1B ≈ +5 h from each start (starts 17:50–19:40). The four masked leaky 4B lanes finish 18:15–18:50 and are the baseline.
Local validation: `/tmp/reg/fixwt_local_validation.log` (fixed-engine corpus `/tmp/drec_fix` replay → weight should be ≈ 0 except hallucination);
`rung1_fixwt_smoke` in /tmp/reg/log (old 1B policy on the new channel; sanity only). Stock WTCHECK/WTREAL now follow the new formula; `WTREAL=2` = old channel.
Next for the fixed policies: rung-1 cert → stock strict (derive v3) → Python rung 4; stock weight mismatch should be ≈ 0 → the 2B gap should shrink by the
weight cost measured by `stock_wtreal_s21` (lands ≈ 19:40) minus the calendar cost (`claim2b_fakeclock_s21`, local, ≈ 18:40).
**17:55 binaries for certifying the fixed policies (derive 24c65e8b, weight 0/1.3M on the fixed-engine corpus):** local stock + libnhagent rebuilt
(md5s in /tmp/reg/build_stock_24c6.log, build_gym_24c6.log), drone stock fa8487127fa1. Local fork eval binary `./puffer` 2261edd25d64 and
`vendor/fast-nle/build/libnethack.so` 12790761052c are the FIXED engine (f7d8749ab) — rung-1 certs of fixed policies use them; certs of leaky
policies on the fixed engine are still valid for the 1B (13,154 vs 13,060) but note the engine in the START line.
**19:00 RESULT: the 2B stock gap IS the weight leak.** stock_wtreal_s21 (leaked weight injected) 16,354 / 9,790 vs canary3 14,559 / 8,730 (+12 %), = fork 16,520 / 9,839.
Guard +5 % (keep), form mask 0, derive v3 0, calendar 0 (fakeclock 14,439 / 8,799). Leaky 4B s602 on the fixed engine: 20,141 / 10,396 (predicts its stock cert,
local `stock_leaky4b_s602_s21` ≈ 21:00). Derive round 2 COMMITTED ed2422e9 (validated on corpus 4: weight 0, capacity 0.016 %, intrinsics 0.10 %, hero_tile 0.11 %, peaceful 0.30 %); known residuals: blessed see-invisible potion (inherent), 17+ object pile window loses page 1 (interface limit),
invisible hero self-look (needs ^X), spells at T=1 (bench ordering).
**19:25 binaries (derive ed2422e9):** local stock + libnhagent rebuilt (md5s in /tmp/reg/build_stock_ed24.log, build_gym_ed24.log); drone stock 1b8ad6cbde77.
The running local `stock_leaky4b_s602_s21` cert uses the older c4f51799e00f (derive 24c65e8b, weight-exact) — note it in its ledger line.
peaceful_at FIXED (0.017 % on corpus 5; probe text read before --More--, thrown miss = re-look): derive HEAD after commit below. Remaining: ^X fallback (invisible hero self-look; identity on
Friday 13th), spells at T=1 (bench ordering), blessed see-invisible potion (inherent).
**19:45 derive final for tonight:** all observation channels exact or ≤ 0.14 % (corpus 5, /tmp/drec_fix5). Stock binaries rebuilt on both boxes from this
commit; ONE drone cert queue `nh_certq_fix.sh` (queue file /workspace/sweeps/nhfix/certq_fix; kinds fork/stock = fixed lanes on the fix tree + stock 5500f55eeafb, forkleaky = leaky 4B on /workspace/pufferlib): fork+stock fixwt1b_s701/702, forkleaky nlestock4b_s602/601/603/604, then fixwt2b, fixwt4b. Starts on idle GPUs (≈ 00:30). Restart via `bash /workspace/sweeps/certq_restart.sh` (kills by PID from a file — a pattern in the ssh command line killed my own shell once tonight).
**19:50 audit of the six fixwt lanes PASSED:** trainer args identical to the leaky claim lanes (diff empty; only seed/run_id/total_timesteps differ), fixed
libnethack acd4252e2c4e mapped in all six, env = NETHACKDIR (fix tree) + NH_NLE_OPTS=1 only, nethack.h/netlib.h/fs.h byte-identical to the evaluators' tree,
checkpoints flowing. Local: `stock_leaky4b_s602_s21` (≈ 21:00) and `r4_leaky4b_s602` (python rung 4, ≈ 20:45) → the fallback claim numbers.

## 20:15 — LIVE QUEUE AT COMPACTION (read this section first)
**Established today:** 1B ladder closed at all rungs; the 2B's −13 % on stock = the weight leak (wtreal 16,354 / 9,790 = fork); fork fixed f7d8749ab;
derive final 4d4eb7e9 (every channel exact or ≤ 0.14 %, peaceful 0.017 %); AutoAscend's published bot owns the env loop exactly like our rung 4 (no inversion needed).
**Drone (8 GPUs training):** fixwt1b_s701 (gpu2, ≈ 23:20), fixwt1b_s702 (gpu1, ≈ 23:30), fixwt2b_s703/704 (gpu5/7, ≈ 04:00–04:30), fixwt4b_s705/706 (gpu0/3, Sunday
≈ 13:00–15:00), leaky nomask s607/608 (gpu4/6, ≈ 04:00; user keeps them). ONE cert queue `nh_certq_fix.sh` (queue /workspace/sweeps/nhfix/certq_fix): fork+stock of
fixwt1b_s701/702, forkleaky (own engine) nlestock4b_s602/601/603/604, then fixwt2b/4b fork+stock; gates on FINAL checkpoint (≥ 990M/1.99B/3.99B) + trainer exit,
NOT on DONE lines (stale 17:33 DONE lines exist for every fixwt lane). Results → /workspace/sweeps/certq/equiv/equiv.log. Restart via `bash /workspace/sweeps/certq_restart.sh`.
**Local (4090):** `stock_leaky4b_s602_s21` (older derive 24c65e8b, seed 21, 10K, ≈ 21:15; at 5,843 read −16 % vs the fixed-engine fork — NOT readable yet);
`r4_leaky4b_s602` (python rung 4, final derive, 480 games, ≈ 20:45; at 183 games ≈ 20.6K / 10.4K = level with the fixed-engine fork 20,141 / 10,396);
queued: `stock_leaky4b_s602_s7` (final derive, seed 7 = the fork seed, 10K; starts after the seed-21 cert; ≈ 23:30) = the clean pair for the leaky 4B;
`fixed1b_tonight.sh` waiter (gated on ckpt ≥ 990M + trainer exit) → `rung1_fixwt1b_s701_s21` (fixed engine, seed 21, 6K, ≈ 23:35) then `stock_fixwt1b_s701_s21`
(seed 21, 6K, ≈ 01:00) → compare with the leaky 1B rung1_s21 13,060 / 8,618 and canary_fix 12,785 / 8,522. All results → /tmp/reg/log.
**Decision rules:** fixed 1B: fork ≈ stock (parity) is the pass; both vs the leaky 1B tell the oracle's value. Leaky 4B: quote only the seed-7 pair (fixed-engine fork
20,141 / 10,396 vs stock seed 7) and the python run; its stock cert is the Monday fallback claim (median ≈ 10.4K ≈ 2× AutoAscend). Fixed 2B/4B: same three-way table.
**Binaries:** local stock 45c6178519da + libnhagent b1d7f6ef40e9 (derive 4d4eb7e9), local fork eval `./puffer` 2261edd25d64 = FIXED engine; drone stock 5500f55eeafb,
drone fix-tree puffer 33bb145ac317, leaky tree puffer at /workspace/pufferlib (dfbdc84c8 engine). Weights local: resources/nethack/{claim2b_s503,pkgnle_s406,nlestock4b_s602}.bin.
**Open user decisions:** stop nomask s607/608 to free GPUs (recommended, user undecided); python rung 4 of the best fixed 2B Sunday morning; cleanup (~1 day) after the claim;
`act(obs)` inversion dropped (AutoAscend doesn't do it). **Rules that bit tonight:** never gate on a log line; never kill by pattern from an inline command
(killed my own shell twice); recorder needs the GPU alone (segfault beside two evals).

## 22:05 — OVERNIGHT QUEUE (user: "wake up to the 1B policies evalled on the various interfaces to prove equivalence")
Local (4090), all self-logging to /tmp/reg/log, pids in /tmp/reg/overnight_pids:
- `fixed1b_tonight.sh` (pid 2373764): fixwt1b_s701 → fetch ckpt → `rung1_fixwt1b_s701_s21` (fork, fixed engine, seed 21, 6K) → `stock_fixwt1b_s701_s21` (strict, seed 21, 6K).
- `fixed1b_s702_tonight.sh` (pid 2455683): fetch fixwt1b_s702 ckpt (atomic .tmp+mv) → waits for pid 2373764 to exit → `rung1_fixwt1b_s702_s21` → `stock_fixwt1b_s702_s21`; ends with FIXED1B_LOCAL_DONE.
- `r4_fixwt1b.sh` (pid 2455686): python NetHackChallenge-v0 24×20 for s701 then s702 (gates on each weights file = 62,208,544 bytes and stable); ends with R4_FIXED1B_DONE.
- `stock_leaky4b_s602_s7` (running since 21:06, ≈ 23:15) = the clean pair for the leaky 4B fork 20,141/10,396.
- `bash /tmp/reg/morning_report.sh` prints the whole table (local + drone) — run it first on Sunday.
Drone: cert queue `nh_certq_fix.sh` unchanged (fork fixed-engine seed 7 14K + stock strict seed 21 10K for fixwt1b_s701/702 as their GPUs free ≈ 23:20/00:00, then forkleaky 4B ×4, then 2B/4B).
References for the table: leaky 1B seed 21 fork 13,060/8,618, stock 12,785/8,522, python 12,900/8,389. Pass = fork ≈ stock ≈ python per policy; fixed-vs-leaky = the oracle's training value.
Also tonight: form-mask audit committed (99299a45): mask wrong-on 0.0017 % of keys, all after silently lost revert messages (65 % of reverts print mid-key and only the first page survives — same for the training env); expiry is the cap; HD-drop clear proposed for the next env round. Leaky 4B: python 480 games 9,869/18,990; stock s21 10K 8,623/16,695.
**23:25 additions (user: "a good amount of work queued for overnight"):** local `r4_more.sh` (CPU, after r4_fixwt1b): leaky 4B gym rounds 2+3 (pool to 1,440 games), then
gym runs of fixwt2b_s703/704. Local `fixed2b_tonight.sh` (GPU, after the s702 chain): fixwt2b_s703/704 fork+stock seed 21 6K each (≈ 03:30–06:15), then a fixed-1B derive
corpus `/tmp/drec_fix1b` + `derive_replay.sh` (recorder rebuilt e86fa345a308 on the final derive), then three calendar arms of the leaky 4B at seed 21 (fake clock pinned:
full moon 2026-09-27 12:00 UTC, phase-2 neutral 09-20, new-moon daytime 09-13; pair with real-clock new-moon night 18,241/9,754 and fork 20,133/10,658). Drone
`nh_certq_extra.sh` (GPUs 4/6 once the nomask lanes finish): forkleaky certs of nomask_s607/608 with NH_NO_CANT_HOLD=1 (A/B vs masked 4B forkleaky certs), then generic
workers on the shared cert queue. Leaky 4B stock results tonight: seed 7 final derive 19,504/10,544 (parity), seed 21 final derive 18,241/9,754 (−9 %), pooled −4.7 % mean,
medians level → the claim number; old-derive seed 21 16,695/8,623 was the reconstruction. `bash /tmp/reg/morning_report.sh` prints everything.
**00:10 Sunday — 10-hour queues on both boxes (user: "about 10 hours worth of work queued on both").** Fixed 1B s701 CERTS: local fork s21 6K 14,521/8,856; drone
fork s7 14K 14,365 (se 171)/8,941 = best 1B on the cert protocol (leaky 1B 13,060/8,618); stock s21 (local 6K, drone 10K) and python 24×20 running. s702 landed 00:06,
same chains firing. Local additions: `local_tail.sh` (after fixed2b chain): leaky 2B claim2b_s503 on the FIXED engine s21 6K (oracle-value row), then leaky 4B cert
seeds 32 and 11 (fork fixed-engine + stock 14K each) → ≈ 12:30; `r4_more2.sh`: leaky 4B gym rounds 4–5 → ≈ 10:30. Drone additions: `nh_night_gpu.sh` (queue
/workspace/sweeps/nhfix/night_gpu_q; starts when the shared cert queue file is empty ≈ 04:30; GPUs 1 2 4 5 6 7): leaky 4B fork+stock cert seeds 44/55 (14K), third-seed
(32) 10K stock certs of fixwt1b_s701/702 and fixwt2b_s703/704; `nh_night_cpu.sh`: 48×20 gym rounds of the leaky 4B once ≤ 2 trainers remain (≈ 04:50) until 10:00
(results r4_leaky4b_night_r<k> in equiv.log). Drone libnhagent rebuilt = local hash b1d7f6ef40e9. Pooled-claim plan Sunday: leaky 4B stock strict over seeds 7/21/32/11/44/55
(≈ 40K kept games) + gym ≈ 3–4K games; fixed generation three-way tables 1B/2B (4B Sunday pm).
**Sunday 06:10 — overnight landed (full tables in LEDGER.md "OVERNIGHT RESULTS").** Fixed 1B ×2 on all three interfaces: fork 14.4K/13.2K, stock −3…−9 % per pair (pooled −6 %),
python at fork level (960 games 13,464/9,510); +5.5 % over the leaky 1B. Fixed 2B s703: fork 18,666/11,020 (+13 % vs leaky 2B), stock 16,949/10,036; s704 fork 15,822/9,537, stock+python
≈ 07:00. Leaky 4B own-engine fork = fixed-engine fork (20,306 vs 20,141): the oracle was worth nothing at eval for the 4B. No-mask 4Bs level with masked (form mask irrelevant at 4B).
Claim cert pooled (seeds 7+21, 8,010 kept) 19,188/10,314 vs fork 20,140/10,442 (−4.7 %/−1.2 %); seeds 44/55 stock land ≈ 08:00 (drone), 32/11 local ≈ 13:30. Real gym pooled
2,400 games: median 9,858 (9,265–10,657), mean 18,779 = 1.85× AutoAscend; more rounds running. Fixed 4B lanes land ≈ 12:30.
**06:25 Sunday:** user wants 4K python games per fixed 4B → `nh_gym4k.sh` armed on the drone (144×28 = 4,032 games per lane, sequential, gated on final ckpt + trainer exit;
results `r4_fixwt4b_s70[56]_4k` in equiv.log). Fixed 4B lanes at 2.7B/2.6B, ~47–51K SPS (slowed by night jobs; gym workers reniced to 19) → land ≈ 13:30–14:00; gym 4K ≈ 1.5–2 h each
→ both by ≈ 18:00 alongside their fork/stock certs. Gym throughput measured ≈ 20 games/h/worker on both boxes. Leaky 4B gym reaches ≈ 4,300 games by 10:30 (local r4/r5 + drone r2).
**Sunday ~10:30 — UPSTREAM PR IN PROGRESS** (user decisions: keep the form mask as trained, NLE options = default, ini → 1122 claim hypers). Worktree
`/puffertank/pufferlib-pr`, branch `nethack-stock-nle` off upstream/5.0 (live tree untouched; vendor/fast-nle + raylib symlinked in, untracked). Done: env diff applied
minus the 4 A/B switches (nethack.h +92, fs.h no corpse exception, netlib.h pickup_types default, zero-time mask = NH_ZT_MASK only, set by the backends);
`ocean/nethack/stock/` = nh_derive.h (1,327 lines, all 46 switches gone, bench-identical to live on 128 episodes), nh_stock_backend.c (473 lines: strict challenge
config only, NLE_STOCK_LIB/NETHACKDIR required, NH_STOCK_OPTIONS + NH_STOCK_FIXEDCLOCK the only knobs), gym backend/runner/nhc_agent (--weights required),
analyze.py, gym_analyze.py, fixclock.c, build_gym.sh, README.md; build.sh: engine pinned f7d8749ab1985349425f4c5bd11f70ee2e914854 + `STOCK=1 ./build.sh nethack`;
config/nethack.ini = 1122 values. All three binaries build. Smokes running (fixed 1B s701 seed 21 1,500 games fork + stock → /tmp/reg/pr_smoke.log; gym 2×2 →
/tmp/reg/pr_gym). Remaining: read smokes vs live (fork 14,521/8,856; stock 13,177/8,620 same protocol), commit (plain message, no attribution), push to fork,
open PR against PufferAI/PufferLib 5.0. fast-nle main fast-forward to nle-stock is the USER's push (classifier blocked it): `git -C vendor/fast-nle push origin nle-stock:main`.
Calendar arms (leaky 4B s21): full moon 20,519/10,838, neutral 19,753/10,283 (= fork 20,133/10,658), new-moon night real clock 18,241/9,754; new-moon-day running.
**Sunday 10:40 — PR COMMITTED LOCALLY (not pushed: user pushes).** Worktree /puffertank/pufferlib-pr, branch nethack-stock-nle, one commit on upstream/5.0. Checks: trimmed
derive bench-identical to live (128 eps); PR stock binary vs live stock binary, same seed, deterministic vec, clock pinned: 411/411 games identical; fork/stock/gym smokes run;
fresh shallow clone fetches the pinned engine sha. PR body draft /tmp/reg/pr_body.md; compare URL https://github.com/PufferAI/PufferLib/compare/5.0...FinlaySanders:PufferLib:nethack-stock-nle
User to run: `git -C /puffertank/pufferlib-pr push fork nethack-stock-nle` and `git -C /puffertank/pufferlib/vendor/fast-nle push origin nle-stock:main`.
**Sunday 11:10 — live tree /puffertank/pufferlib is CHECKED OUT ON `nethack-stock-nle` (6b291871) for the user's review; worktree /puffertank/pufferlib-pr removed.**
scripts/nle_stock is not on this branch (campaign tree = `git checkout nle-stock`); ledger entries wait until then (results keep landing in /tmp/reg/log). Local box idle:
all local eval chains stopped (leaky 4B seed-32 cert killed mid-run, seed-11 pair and 2B confirmation cancelled, fixed4b_local cancelled). Leaky 4B claim cert is CLOSED at four
seeds: stock 19,320 (se 156) / 10,502 over 28,010 kept vs fork 20,240 / 10,461 (−4.5 % / +0.4 %); median 1.97× AutoAscend. Drone: fixed 4Bs land ≈ 13:00/13:30 → fork s7 14K,
stock s21 10K, gym 4,032 games each (nh_gym4k.sh) ≈ 17:30. DESIGN.md untracked in ocean/nethack/stock (user decides). User pushes the branch + fast-nle main themselves.
**Sunday 11:50 — stock tooling MOVED to fast-nle `stock/`** (user: keep all NLE stuff in one place). fast-nle nle-stock local commit bf7aa1e2e (not pushed) = stock/ dir;
PufferLib working tree (branch nethack-stock-nle, uncommitted, at upstream/5.0) now = env 3 files (+66 nethack.h), build.sh (pin bf7aa1e2e + STOCK=1 → $NLE_DIR/stock),
config ini, .gitignore. NH_EPLOG moved from the env into the stock backend (7 columns: score how turn noprog role race gender; analyze.py unchanged). Gym key log, verbose,
idlog, nomidlook and the obs hashes removed. Drafts: /tmp/reg/pr_commit_msg.txt, /tmp/reg/pr_body.md. User pushes: fast-nle nle-stock→main, PufferLib branch.
**Sunday 12:15 — build moved out of PufferLib entirely** (user: keep build.sh as it was). PufferLib diff = 3 env files (+66 nethack.h) + config ini only (85/25 lines).
fast-nle stock/: build.sh builds stock/build/libnethack.so (backend as a drop-in for the fork lib) + stock/libnhagent.so; puffer_stock launcher = LD_LIBRARY_PATH override
(puffer has RUNPATH, so LD_LIBRARY_PATH precedes it; fork lib never loaded — LD_PRELOAD would be WRONG: 2,288 symbol names shared with the fork lib). Pin removed from
PufferLib; fast-nle main must be fast-forwarded. Verification of the launcher path vs the static final binary (pinned seed 33, 411 games) running → then amend the fast-nle
stock commit (build.sh, puffer_stock, .gitignore, docs; build_gym.sh removed). `puffer` in the live tree is the freshly built fork binary (tracked file shows M): exclude from the commit.
**12:25 — FINAL PR STATE.** PufferLib (branch nethack-stock-nle, uncommitted, upstream/5.0 base): ocean/nethack/{nethack.h +66, fs.h, netlib.h} + config/nethack.ini; build.sh/.gitignore
untouched. Tracked `puffer` shows M (freshly built fork binary) — exclude from the commit. fast-nle nle-stock: dfbdc84c8, f7d8749ab, b40f4ca8e (stock/ incl. build.sh, puffer_stock; unpushed).
Launcher path verified: pinned seed 33, 411/411 games identical to the static final binary. Drafts: /tmp/reg/pr_commit_msg.txt, /tmp/reg/pr_body.md. User pushes both.
**14:05 — 4th fast-nle commit 70d638314: attribution switches removed; deterministic fork eval identical before/after (10088.493164 over 414 games). nle-stock = 4 commits, unpushed.**

## Sunday 14:30 — PR PUSHED, fixed-4B certs landing, video task started (read this section first)
**BOTH PRs pushed, one commit each titled `nethack challenge` (no trailer — user's standing rule beats the attribution reminder):**
- fast-nle `origin/main` = e7f656856 (was 4 commits: exports + appearance weight + stock/ + switch removal, squashed). PufferLib build.sh clones main with NO pin. Verified: fresh clone of main builds engine + stock backend + gym lib, runs a gym episode; deterministic fork eval identical before/after the switch removal (10088.493164/414 games).
- PufferLib `fork/nethack-stock-nle` + `origin/nethack-stock-nle` = 78f446fe. 4 files (nethack.h +66, fs.h, netlib.h, config/nethack.ini); build.sh/.gitignore back to upstream. PR body draft `/tmp/reg/pr_body.md`; compare https://github.com/PufferAI/PufferLib/compare/5.0...FinlaySanders:PufferLib:nethack-stock-nle (USER opens the PR).
**Verification done on the shipped code:** trimmed derive bench-identical to dev (128 eps); stock binary (static + puffer_stock launcher) 411/411 pinned-seed games identical to dev; NH_EPLOG moved env→backend; per-episode logger, gym key-log/verbose/idlog/nomidlook, obs hashes, zero-state probe all removed; local PR-branch build reproduces drone (s705 stock 18,797/11,760).
**FIXED 4B CERTS (honest, leak-free; the claimable clean-generation numbers):** fork fixed-engine seed 7 10K: s705 19,897/11,562, s706 19,911/10,847. Gym real NetHackChallenge-v0 4,032 games: s705 19,525/11,674 = **2.19× AutoAscend 5,336 (2.37× the 2023 4,918); gym vs fork −1.9% mean / +1.0% median** (tighter than leaky 4B's ~5% — later in the week, past the new moon). Stock strict seed-21 10K certs running (~15:00/15:10), s706 gym ~16:00. Leaky 4B claim cert (4 seeds, 28K kept) 19,320/10,502 stays the fallback.
**Weights local:** resources/nethack/fixwt4b_s705.bin (md5 3e8fd0f4b3e3, = drone final ckpt). Drone lanes at /workspace/sweeps/nhfix/checkpoints/nethack/fixwt4b_s70{5,6}/0000003999793152.bin.
**VIDEO TASK IN PROGRESS (user asked for videos of interesting play):** plan = vec eval batch with NH_EPLOG (score/depth/turns/role/killer per game) to pick an interesting seed, replay in the demo path (`./build.sh nethack --cpu` → ocean/nethack/nethack.c, NH_WEIGHTS/NH_SEED/NH_SKIP/NH_TRACE getenvs), record the ttyrec (fork engine tmt_write / nle_start FILE*; nle.ttyrec3.bz2 exists in repo root). An Explore agent is investigating the exact recording path — its findings arrive as a task notification; DO NOT predict them. Use fixed 4B s705 as the player. Local box is idle; run there.
**Local monitor task active** (result lines from /tmp/reg/log + drone equiv/long logs). Overnight pids in /tmp/reg/overnight_pids (most now done).

## Sunday 17:20 — 1B/2B gym certs extended to 4K games (RUNNING on drone)
User wants the fixed 1B/2B NetHackChallenge-v0 certs at 4,032 games like the 4B ones (old 480/960-game runs put 2B median
9,495 under 1B 9,591 = small-sample inversion; bootstrap: median sd ±630 at n=480, inversion P=0.17). Launched
`/workspace/sweeps/nh_gym4k_12b.sh` (clone of nh_gym4k.sh: 144 workers x 28 games, nice 5, sequential lanes fixwt1b_s701,
s702, fixwt2b_s703, s704; final ckpts 0000000999817216 / 0000001999896576), same libnhagent b1d7f6ef40e9 + tree 4d4eb7e9
as the 4B certs. Output dirs /workspace/sweeps/certq/equiv/r4_<lane>_4k, DONE lines in equiv.log, ends GYM4K_12B_DONE.
Started 17:18; expect ~25-45 min per lane (4B lanes took 40-80 min). Local monitor bppzp8o2l tails equiv.log.
Then: regenerate resources/article figures (gen_data.py gym table -> update the gym entries with the new 4K pooled stats).
Analysis note for the article: median gains are +11%/doubling (fork 9,098 -> 10,084 -> 11,225) vs mean +25%/+15% because
the bottom third of games (early deaths, weak roles Hea/Tou/Wiz) is identical across sizes; gains are in the tail.

## Sunday 19:25 — article work; state for compaction (read with the 17:20 section)
ARTICLE ("Beating AutoAscend in NetHack with RL"; user's outline: intro -> Let's Talk Score -> Making NetHack Faster ->
Encoders and Decoders -> RL Finds Bugs -> What's next?). Written so far: `resources/article/lets_talk_score.md` (full
section draft, six beats: caveat, headline, how measured + table, what training buys, thirteen roles, the catch). Numbers
must come ONLY from `resources/article/certificates/RESULTS.md` (see [[nethack-results-ledger-2026-09-13]]). Open in the
draft: AutoAscend footnote needs the 2023 re-eval citation; 2B gym row pending; 1B gym updated to 8,919/13,362 (8,064).
FIGURES (`resources/article/`, see [[nethack-article-figures]]): bars_median_gym/bars_mean_gym/bars_median_fork,
roles_median/mean, gap_median/mean, depth_vs_score, score_up_depth_down; web/ light versions; extras parked in out/extra.
The other agent's gen_data.py adapter blocks regeneration until 2B gym lands -> then `python3 certificates/ledger.py
refresh && build`, `resources/article/render.sh`, re-copy to /puffertank/docker/nethack_article (user scps from
`puffer@pufferbox3:puffertank/nethack_article`, see [[pufferbox3-container-paths]]).
DRONE: nh_gym4k_12b.sh lanes: s701 DONE 8,749/14,011; s702 DONE 9,054/12,713; s703 running since 18:59 (~19:55);
s704 next (~20:50); ends GYM4K_12B_DONE. Monitor bppzp8o2l tails equiv.log. Nothing else running anywhere.
TREE: only `puffer` (binary) modified among tracked files; src/constellation.c UNCHANGED (patch never applied);
untracked: resources/article/, scripts/nle_stock/watch/, nethack_videos/, resources/nethack/*.bin; find/watch tooling in
git stash@{0}. Constellation scaling render parked (data staged; would need the export patch with the fixed anchor
`EndTextureMode();\n\n        // Figure 2` — note the blank line).
FINDINGS TO REMEMBER: gym == fork within noise (4B +2.6% median / -1.0% mean; NetHack new-moon phase 0 on 11-14 Sep,
real clock, still parity); calendar effect never established ([[nethack-calendar-effect]]); median gains +11%/doubling vs
mean +25%/+15% because the bottom third (early deaths, Hea/Tou/Wiz) is fixed; training makes play shallower
(Dlvl8+ 9.6->7.2->4.8%), best game 385,778 at Dlvl 7.

## Sunday 21:10 (2026-09-13) — all certs done, speed section researched
- ALL headline certs complete; ledger refreshed+built, independent check 22/22 & 9/9 MATCH. 2B gym pooled 10,345 · 16,753 ± 234 (8,064). Figures regenerated 21:05; `lets_talk_score.md` table complete (2B gym row filled); everything staged in /puffertank/docker/nethack_article (`scp -r puffer@pufferbox3:puffertank/nethack_article .`).
- User's own score-section draft reviewed: fix 11,508→11,516; REWRITE the gap paragraph (gym ≈ fork within seed noise, +2.6% at 4B and 2B; wall-clock effect null — do not cite); qualify "unbeaten" to the Challenge task; stale bars PNG now fixed.
- User parked the score section until 2B landed (done) and chose "Making NetHack Faster" or "Encoders and Decoders" next; I recommended Faster and proposed a 5-beat flow (why fork / what fork is: 471 globals→ctx, oracles / where time went: getenv-in-RNG 45%, 21 fills/step 33%, status line ~25%, TLS bug, LTO+PGO 1.32x / hooks vs probes: 84% of challenge keys are probes, ~5 per action, fork 2.03 keys/step / numbers: 112.8K SPS shipped cfg on 4090+14900K, fork 5.9x stock same box, lanes 4.7/9.5/19.1 h for 1/2/4B six-per-box; leftovers: prompt auto-advance ~2x (21% of steps advance a turn), env pool 1.74x unshipped). Awaiting "write it".
- Fact sheet for the section is in the subagent output (speed campaign memories digest); key sources: vendor/fast-nle/docs/DESIGN.md + DETERMINISM.md, /tmp/reg/mainclone/stock/{README,DESIGN}.md (probe rules + per-hook mismatch table), fork git log (42 commits on 2319f298).
- Local bench artefacts: /tmp/reg/article/sps_bench_512.out (BENCH_RC=134 = teardown abort after all 152 epochs, numbers valid), /tmp/reg/article/pair/{fork,stock}.out, ./puffer_bench binary (clean build, untracked).
- Nothing running locally; drone idle (GYM4K_12B_DONE 21:03). Monitor bppzp8o2l still armed on the drone logs (harmless).

## 2026-09-27 — state after two weeks of other-agent work (read WORK_STATUS.md at repo root first)
- Repo now on branch `drone-nominal-actions` (HEAD 3719caaa "small cleanup", 1cb95a8a "cublas fix" merged after PR #690 nethack-stock-nle). `/puffertank/pufferlib/WORK_STATUS.md` (26 Sep, other agent) is the status summary; `/puffertank/experiments/<name>-2026MMDD/` holds every experiment with REPORT/RESULTS.md.
- Score ledger `resources/article/certificates/RESULTS.md` UNCHANGED since 09-13 21:13 (results.csv byte-identical to my staged copy).
- NEW AutoAscend in-house re-eval (`resources/article/autoascend/`): 8,064 attempts on real NetHackChallenge-v0 on the drone, pinned commit 8527910, panic_on_errors, 720 s timeout: median 5,527.5 / mean 8,988 (7,610 completions, 446 agent exceptions, 8 timeouts, last live score retained); incomplete-as-zero median 4,444 / mean 7,661. 4B RL = 2.08x median / 2.19x mean vs this. FIGURE_NOTES.md says bars now use this baseline; article_draft.md prose still says 2.16x vs 2021's 5,336 — INCONSISTENT, reconcile.
- NEW depth-trained cohort: 2B seeds 801–808 (`/workspace/experiments/nethack-depth-2b-20260914`), 80K fork games; BALROG progression mean 15.31% vs score-4B 11.48%; Medusa/Castle exact visitation (landmarks/): seed 801 732 Medusa / 230 Castle per 10K, Archeologist dominant; Castle arrival video (castle-video-20260914, Elven Priest depth 27). Depth config retrain s906 (09-24): 2B in 2h15m at ~247K SPS (cuBLAS fix), mean max depth 10.7, max 29, BALROG 15.9%.
- Engine microbench (`benchmark/`): 8 P-cores, replayed keys: 512 games fast-nle 720K keys/s vs Python challenge 90K (8.05x) vs stock-C 110K (6.6x); 1,024 games 5.4x; single game stock C is FASTER than fast-nle (0.46x) — say "at scale" only.
- Article: `article_draft.md` = consolidated script (Results, roles, Let's Talk Score, Making NetHack Faster, Neural NetHacks); remaining sections RL Finds Bugs (source `bugs/AUDIT.md`, 7 engine bugs w/ fork commits + NLE/NetHack 5.0 status) and What's Next. 24 figures in out/ incl. policy_architecture/encoder/decoder, roles_depth_*, landmark_reach*, inventory_encoder_supervised, message_encoder*. `linkedin_post.md` at repo root (uses 2.08x).
- cuBLAS fix (memory cublas-stream-workspace.md): +54% long-horizon NetHack throughput; repeatability restored.
