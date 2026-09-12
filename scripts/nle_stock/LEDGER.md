# NetHack stock-NLE claim — cert ledger

Single source of truth for **which weights were trained on which tree, and which cert numbers belong to which
(weights, tree, interface)**. Updated 2026-09-11 18:50. Box = `ssh drone`.

## The one rule

Only one kind of number is a cert: `analyze.py` **burn-in-adjusted mean / median** over a per-episode `.ep` log
(512 agents, 14,000 episodes, drop the first 4,000, take the next 10,000). Two other numbers look like scores and
are not certs:

| looks like | what it is | noise | where it shows up |
|---|---|---|---|
| panel `score 13415.348` at end of training | rolling window average at the final epoch | ±1000 (3-seed spread 12,448–13,497 on identical config) | `long.log` `score=`, `.ini [metrics]` last point |
| `CUDA_EVAL ... score=11393 games=14059` | raw mean over every game incl. the 4,000 burn-in episodes, no `.ep` | biased low by burn-in | local `./puffer eval` without `NH_EPLOG` |
| `analyze.py ... burn-in-adjusted mean=13576 median=8008` | **the cert** | se ≈ 170 at 10,000 post-burn-in eps | `results.log`, `chalcert.log`, `baseline.log` |

The "15% repo-vs-box gap" (11,394 vs 13,081) compared row 2 against row 1. It was never a like-for-like number.

## Trees

| tree | lib | puffer | stock bin | export changes | cant_hold | NH_NLE_OPTS | role |
|---|---|---|---|---|---|---|---|
| box `/workspace/PufferLib` | `44dd5b181dc3` | `7a7ca8b29459` (`c803625c00d6` for nleopts lanes) | `f9619728ec1d` | nle_abl + gem_canon; **no** `internal[5]=0`; engr_blind partial | no | no | trained `rt_1B_1122new/pub/nleopts`; certq/attr2 certs of the t1122 champion |
| box `/workspace/PufferLib_pkg` | `bdb9896bd881` | `feb7d8c938b0` | `db21b1101083` | all four | **no** | yes | **the claim tree** — trained `pkg_s40x`, `iso_s4xx`, `pkgnle_s406/407`, `claim2b_s50x`; all challenge certs |
| **branch `nle-stock`** — local `/puffertank/pufferlib` and box **`/workspace/pufferlib`** (clean clone) | `e54561117397` local / `9886d5df82f0` box (both engine `dfbdc84c8`, identical to the training engine on 34/34 goldens) | `ae85c117d61f` / `6689a4bb9aec` | `12376464d70c` / `6b529125580c` | all four | **yes (8 sites, reset per episode)** | yes | pufferlib `5dee1bd4` = HEAD `c7590188` + every claim-tree hand edit + cant_hold + `scripts/nle_stock/`. **The one tree from 2026-09-11 20:10.** Box also has `/workspace/nle-venv` (stock NLE 0.9.0 installed from the untouched `/workspace/nle-stock`, gym 0.23) for rung 4. Nothing has trained on it yet; the first lane from it produces the first same-tree weights. |

Stock NLE package: box `/workspace/nle-stock` and local `/puffertank/nle-stock` are byte-identical
(537 `.c/.h`, `84c24e5a811b3298`, build dirs excluded); local is git-clean at upstream `862a439a8`.

## Weights

| weights | steps | trained on | options | final ckpt | panel final (not a cert) |
|---|---|---|---|---|---|
| `nethack_t1122_2B_weights.bin` (`c19c7fef0e7d`) | 2B | pre-export champion tree | training | — | — |
| `rt_4B_1122_s204` | 4B | pre-export | training | last `.bin` | — |
| `rt_1B_1122pub_s301` | 1B | PufferLib, public obs | training | | — |
| `rt_1B_1122new_s301/302/303` | 1B | PufferLib `44dd` | training | | 12,448 / 13,219 / 13,497 |
| `pkg_s401/402/403` | 1B | pkg | training | | 12,347 / 12,828 / 13,050 |
| `iso_s411/404/405` | 1B | pkg | NLE opts + `pile_limit:0` kept | | 12,834 / 12,816 / 14,561 |
| **`pkgnle_s406`** | 1B | pkg | NLE opts | `0000000999817216.bin` `b126512c6fbc` (= local `resources/nethack/pkgnle_s406.bin`) | 13,415 |
| **`pkgnle_s407`** | 1B | pkg | NLE opts | `0000000999817216.bin` `841755e7e25c` | 13,260 |
| **`claim2b_s503`** | 2B (1,999,896,576) | pkg | NLE opts | `0000001999896576.bin` `a87dd4f2445c` | 16,579 |
| **`claim2b_s502`** | 2B (1,999,896,576) | pkg | NLE opts | `0000001999896576.bin` `dd9cc983bbac` | 16,618 |
| **`claim2b_s501`** | 2B (1,999,896,576) | pkg | NLE opts | `0000001999896576.bin` `ed679c6…` | 15,977 |
| **`nlestock4b_s601/602/603/604`** | **4B, TRAINING** (started 23:00–23:09 2026-09-11) | **nle-stock `423ced55`** (`/workspace/pufferlib`, engine `dfbdc84c8`, lib `9886d5df82f0`, puffer `2bd99678fe40`) | NLE opts, **sticky** extended `cant_hold` (the version later found to cost 12 % on stock certs; fork-side cost bounded ≤ 2–3 % by rung 1), zero-time mask OFF | — | ETA ~18:00 2026-09-12 |
| `nlestock4b_s605/606` | stopped at 393M (09:12) | same as above | | — | replaced below |
| **`nlestock4b_nomask_s607/608`** | **4B, TRAINING** (started 09:12 2026-09-12 on gpu4/gpu6) | nle-stock `a51b1953` (puffer `6b833e79cb08`) | NLE opts, **`NH_NO_CANT_HOLD=1` — no form mask at all**; otherwise identical | — | ETA ~01:00 2026-09-13; 4-vs-2 = training-side cost of the form mask |
| `claim2b_s504` | **segfaulted at 1.57B** | pkg | NLE opts | `0000001572864000.bin` | 13,815 |

## Certs — by interface

Numbers are burn-in-adjusted **mean / median**; `(n)` = post-burn-in episodes when short of 10,000.

### Rung 1 — fork interface (`./puffer eval`, the training interface)

| weights | tree | arm | mean / median |
|---|---|---|---|
| t1122_2B | PufferLib | `new2b_s7` | 15,501 / 9,600 |
| t1122_2B | PufferLib | `new2b_s11` | 15,469 / 9,751 |
| t1122_2B | PufferLib | `lazy2b_s7` (NLE_ABL=7) | 15,136 / 9,630 |
| t1122_2B | PufferLib | `gemtrue2b_s7` | 15,668 / 9,884 |
| t1122_2B | PufferLib | `gemtrue2b_s11` | 15,668 / 9,884 — **identical to s7: `box_attr2.sh` hardcodes `--base.seed=7`, every attr2 "s11" is really seed 7** |
| t1122_2B | PufferLib (pile_limit removed) | `nopile2b_s7` | 15,198 / 9,536 |
| t1122_2B | PufferLib | `pubbase2b_s11` (seed 7, see above) | 15,565 / 10,027 |
| rt_4B | PufferLib | `new4b_s7` | 17,684 / 9,740 |
| pub_s301 | PufferLib | `forkpub301_s7` | 13,742 / 8,880 |
| **pkgnle_s406** | **pkg** | `fork_pkgnle_s406_s7` | **13,350 / 8,706** (panel final 13,415, Δ −65) |
| **pkgnle_s406** | **pkg** | `fork_pkgnle_s406_s11` | **13,260 / 8,634** (Δ −155) |
| **pkgnle_s407** | **pkg** | `fork_pkgnle_s407_s7` | **13,542 / 8,238** (panel final 13,260, Δ +282) |
| **pkgnle_s407** | **pkg** | `fork_pkgnle_s407_s11` | **13,264 / 8,072** (Δ +4) |
| **claim2b_s503** | **pkg** | `fork_claim2b_s503_s7` | **16,027 / 9,432** (panel final 16,579, Δ −552) |
| **claim2b_s503** | **pkg** | `fork_claim2b_s503_s11` | **16,417 / 9,623** (Δ −162) |
| **claim2b_s502** | **pkg** | `fork_claim2b_s502_s7` | **16,795 / 10,248** (panel final 16,618, Δ +177) |
| **claim2b_s501** | **pkg** | `fork_claim2b_s501_s7` | **16,440 / 9,922** (panel final 15,977, Δ +463) |
| **pkgnle_s406** | **nle-stock `/workspace/pufferlib`** (equiv) | `r1_pkgnle_s406_s7` | **13,337 / 8,908** — one-tree run, with `cant_hold` |
| **pkgnle_s406** | **nle-stock `/workspace/pufferlib`** (equiv) | `r1_pkgnle_s406_s11` | **13,613 / 8,943** — matches `PufferLib_pkg` rung 1 (13,350 / 13,260); `cant_hold` neutral on the fork |
| pkgnle_s406 | local repo | `fork_s101/s102` | 11,394 / 10,959 **raw CUDA_EVAL means, no .ep — not certs** |

### Rung 2 — stock harness, non-strict (`puffer_nethack_stock`, reconstruction + probe crutches)

| weights | arm | mean / median |
|---|---|---|
| t1122_2B | `stock2b_s7` | 13,847 / 8,072 (5,182) |
| t1122_2B | `stock2b_s11` | 14,103 / 8,148 (5,163) |
| t1122_2B | `cert_2b_s7` | 13,447 / 7,896 (7,153) |
| t1122_2B | `cert_2b_s11` | 13,576 / 8,008 |
| t1122_2B | `cert_2b_s13` | 788 eps only, killed |
| rt_4B | `stock4b_s7` | 14,615 / 7,952 (1,378) |
| rt_4B | `cert_4b_s7` | 2,605 eps only, killed |
| pub_s301 | `stockpub301_s7` | 12,914 / 8,112 (5,338) |
| **pkgnle_s406** | `rung2_pkgnle_s406_s21`, `_s32` | **RUNNING** (box gpu0/gpu7, launched 19:27, `rung2.log`); NLE options, crutches on, no strict rule; pairs with rung-1 and `chal_s21/s32_real` |

### Rung 3 — challenge configuration (STRICT, NLE literal options, NOSDESC/NOREDRAW/STOCKSORT/NODARKFIX/NOTOPL, real clock, 1e6 step cap, 10K stall cap)

| weights | arm | mean / median | note |
|---|---|---|---|
| pkgnle_s406 | `claim_406_s7` | 11,237 / 6,828 | 14,011 eps; ran with `NH_STOCK_CLEAREOS=1`; 3 sibling arms segfaulted |
| pkgnle_s406 | `chal_s21_real` | 11,376 / 7,138 | (6,026) |
| pkgnle_s406 | `chal_s24_fake` | 11,152 / 7,018 | (6,012) frozen clock |
| pkgnle_s406 | `chal_s32_real` | 11,539 / 7,336 | (6,031) |
| pkgnle_s406 | `chal_s33_real` | 11,247 / 6,883 | (6,000) |
| pkgnle_s406 | `claim_406_s11` | 12,111 / 7,424 | (1,871) killed |
| pkgnle_s407 | `claim_407_s11` | 11,617 / 6,612 | (1,849) killed |
| pkgnle_s407 | `claim_407_s7` | 3,586 eps only | killed |
| claim2b_s504 @1.57B | `chal2b_claim2b_s504` | **11,813 / 6,957** (6,015 post) | done 21:20; aborted 1,514 / 10,015 = **15.1%** (no `cant_hold` on this tree) |
| **claim2b_s503** | `chal2b_claim2b_s503` | **RUNNING** (gpu3, since 18:44) | |
| **claim2b_s502** | `chal2b_claim2b_s502` | **RUNNING** (gpu2, since 19:05) | |
| **claim2b_s501** | `chal2b_claim2b_s501` | **RUNNING** (gpu1, since 19:24) | all three 2B lanes now in both rung 1 and rung 3 |

### Rung 4 — the real `NetHackChallenge-v0` gym env (Python, `nhc_agent.py` → `libnhagent.so`, CPU policy, `reset`/`step` only)

Analyse with `gym_analyze.py <dir>` (equal-k headline; `plen` is cumulative per worker). Results in `results/gym/`.

| weights | run | episodes | median (equal-k) | note |
|---|---|---|---|---|
| pkgnle_s406 | `single` (24 × 1) | 24 | **7,210** | one episode per process — the only earlier run free of the ratchet below |
| pkgnle_s406 | `fixed_pkgnle` (16 × 20) | 320 | 1,479 | **invalid**: ep1 median 6,462, ep2+ 1,394; 14/16 workers collapse permanently — `cant_hold` ratchet |
| pkgnle_s406 | `pkgnle`, `pkgours`, `run4` | 187–317 | 1.4–2.2K | invalid, same ratchet (all built from `wt_gate`, which had `cant_hold` without the reset) |
| pkgnle_s406 | `fixed_reset_pkgnle` (16 × 20) | 320 | **8,270** (mean 12,260) | **DONE 20:07**, local repo tree (has `cant_hold`) — a mechanics check, not a claim-tree number. Leak gone: 0/16 collapses, eps 1–10 vs 11–20 P=0.49. Aborted by the challenge env **3.4%** (rung 3 on the box, no `cant_hold`: 11–14%). Episode 1 alone reads high (13,000, n=16, P=0.65 vs rest, ~2σ) — unresolved, not accumulating. Our C-side `maxnoprog` field is read after the auto-reset and is wrong for aborted rows; NLE's `end_status` is the trustworthy field. |

| pkgnle_s406 | **equiv `r4_pkgnle_s406`** (24 × 20, box `/workspace/pufferlib` + `/workspace/nle-venv`) | 480 | **7,033** (mean 10,777) | **one-tree run, done 21:03.** Same tree as the equiv rung 1 (13,337 / 8,908; 13,613 / 8,943) → one-tree fork→Python gap **−19% mean, −21% median**. Episode-1 median 3,640 (n=24): the earlier "episode 1 high" was noise. |

Smoke on the rebuilt library (19:00): one real challenge episode, 749 policy steps, 7,157 env steps, 5,132 probes, no faults.

Reference: AutoAscend, 2021 NetHack Challenge winner, **median 5,300** (4,096-episode test phase).

## What we expect each rung to cost

- Rung 1 vs panel final: **≈ equal** — **confirmed 2026-09-11 18:39** for `pkgnle_s406/407`: four arms within −155…+282 of their panel finals (se ~160), real `rc=0`. Tree, weights and protocol are coherent; there is no cert regression.
- Rung 2 vs rung 1: t1122_2B shows **−10 %** (15.5K → 13.5–14.1K). Reconstruction imperfections + probe steps.
- Rung 3 vs rung 1: pkgnle_s406 challenge sits at 11.2–11.5K against a 13.4K panel final, **≈ −15 %**. Probe budget (~10–14 env steps per policy step) against the 1e6 cap and the 10K stall abort (9–11 % of episodes abort).

## Loop census and mask A/B (local 4090, one tree, 2026-09-11 evening)

Strict challenge configuration, `pkgnle_s406`, seed 21, 6,000 episodes per arm, burn-in adjusted:

| arm | masks | mean (se) | median | aborted |
|---|---|---|---|---|
| A | `cant_hold` only (pre-mask binary) | 10,503 (275) | 6,128 | 3.7% |
| B | + per-message WEAR/THROW/KICK/bump | 10,938 (287) | 6,586 | 1.5% |
| C | general zero-time rule v1 + extended `cant_hold` | **below A**: at equal completion (5,372 eps) post-burn-in mean 9,621 vs A 10,416, all-episodes 8,915 vs 10,055, P(C>A) = 0.475 (≈3σ) | | 1.6% |
| D | = A, with the toplines-restore crutch ON (message-channel probe) | ≈ A or slightly below (P = 0.479) | | **5.7%** |

Readings: **the per-message masks are neutral (ship: B's extended `cant_hold`)**; **the general zero-time rule v1 costs ~8%** —
its "world unchanged" test (x, y, depth, clock) misreads a fast hero's extra-speed actions as refusals and masks a landed
attack until the turn ends; kept in the tree **opt-in only** (`NH_ZT_MASK=1`) until the unchanged test covers the whole
observation (v2). **D rules out the message channel**: restoring the engine's toplines across probes does not reduce
loops (aborts 5.7% vs 3.7%), so the stock-induced loops come from the observation content, not from hidden refusal text.

P(B > A) = 0.509: the masks cut aborts without moving the score — aborts are worth ~2–4 % of mean, as the
abort arithmetic predicted (0.116 × (11,083 − 9,056) ≈ 235 on the old rung 3).

**Rung-1 loop census** (fork, training interface, same masks as A, 4,046 eps, new `.ep` column = worst run of
zero-time policy steps): runs ≥ 1,000 steps (≈ the challenge's 10K-env-step abort) in **0.5 %** of games;
≥ 500 in 0.8 %; ≥ 100 in 1.9 %; p99 = 314. Stock with identical masks aborts 3.7 %, without `cant_hold` 11–14 %.
**The stock interface induces zero-time loops 7–25× more often than the fork does.** The loops are a symptom of
reconstruction error (observation, post-probe message channel, or derived mask inputs), and the abort rule is
only the part of it the referee makes visible.

## Overnight 2026-09-11 → 12 (what runs where, and why)

| machine / GPUs | job | why | lands |
|---|---|---|---|
| box gpu1,2,3,5 | **4B × 4** `nlestock4b_s601-604`, nle-stock `423ced55` | the claim weights on the one tree; priority job | ~14:30 |
| box gpu0,7 | rung 2 `pkgnle_s406` (non-strict stock) | integrated reconstruction+probe cost, holds the referee fixed | readable ~01:00, done ~05:30 |
| box gpu4,6 | one-tree rung 3 `pkgnle_s406` (with `cant_hold`) | same-tree rung 3 vs rung 4; `cant_hold` A/B on rung 3 | ~01:00 |
| box gpu4,6 after | **reconstruction ablation, seed 32** (21 arms, harness `b7c061bf0a47`) | doubles the power of the per-channel cost table | ~08:00 |
| box gpu0,7 after | rung 3 of the old 4B `rt_4B_1122_s204` on the one tree | what a 4B does on stock today: the reference for the new 4B's rung 3 | ~09:30 |
| local 4090 | **reconstruction ablation, seed 21** (21 arms, harness `9d2114095b40`) | the per-channel cost table | ~06:00 |

The first local ablation attempt (23:00–23:07) ran a harness linked against the scratchpad worktree's engine
(`3a3fd3811e7f`, the parked perf build) — the wrong-library trap for the second time today — and was discarded
(`/tmp/ablate_WRONGLIB_2307`). The stock binaries link no fork library (they dlopen stock), so no cert was affected.
Build scripts now fail if the linked `libnethack.so` is not this tree's.

## CERT REGRESSION FOUND — 2026-09-12 09:05: the sticky `cant_hold` cost ~12% mean / ~19% median on stock

Same tree, same weights, seed 21, strict challenge configuration, 6,000 episodes, burn-in adjusted:

| arm | `cant_hold` | mean | median | aborted |
|---|---|---|---|---|
| A | sticky (as shipped 2026-09-11) | 10,503 | 6,128 | 3.7% |
| **X1** | **off** (`NH_NO_CANT_HOLD=1`) | **11,956** | **7,540** | 11.1% |
| X4 | expires after 100 turns (`a51b1953`, now default) | running, tracking X1 | | |
| old tree `PufferLib_pkg`, no `cant_hold` (box, 10,000 eps) | — | 11,376 | 7,138 | 11.6% |

Mechanism: the flag is set from form-refusal messages (all engine sites are form tests, so sets are sound) but
cleared only by "You return to…" / "You turn into…". On the fork that message is always seen; on stock a probe or a
`--More--` can eat it, and a hero back in human form keeps WIELD/THROW/WEAR/ENGRAVE masked for the rest of the game.
Rung 1 was equal across trees (13,337 vs 13,350) and the fork loop census with the shipped masks is 0.42%, so the
**4B lanes' training interface is unaffected**; the damage was to the stock cert only. Everything else was ruled out
byte-for-byte first: derive/backend/tables identical between builds, build flags identical, switch sets and engine
banners identical, upstream `ocean/nethack` drift is demo rendering plus an obs-buffer refactor.

Also closed: **E** — zero-time mask v2 (masks on the second identical zero-time step): **1 abort in 6,062**, score
neutral vs A (P=0.499; post-burn-in 11,143 / 6,491). Candidate for default once re-measured on top of the expiring
`cant_hold` (E2). All one-tree rung-3 numbers recorded above (10,229 / 10,310) carry the sticky-flag penalty.

Lesson (now in memory): a belief learned from a message channel that can drop messages must expire or be
re-verified; and a cert canary (fixed-seed strict rung 3 against the previous build) gates env/derive changes.

## Reconstruction ablation — morning of 2026-09-12 — **INVALID, superseded** (kept for the record)

**Retracted 07:20.** These arms ran the harness **without `NLE_GETPOS_NORMAL=1`**, which the fork needs so the farlook
probe gets a real cursor prompt (the fork's `getpos` returns at once by design; earlier harness work always set it —
"otherwise kills probes"). The tell: the harness looped in 23% of games while the real stock backend with the same
derive and probes aborts 3.7% — the harness was not measuring stock. Corrected rerun `/tmp/ablate_gp` (real0, derived,
+6 channels) queued behind arm E. The honest integrated number for probes+reconstruction on stock remains rung 2 vs
rung 1: ≈ −13% mean. Original (invalid) table:

(fork engine, harness, paired seed 21, 3,000 eps/arm; seed 32 on the box agreed with the first three rows)

| arm | policy sees | mean | median | eps with a ≥1,000-step zero-time loop |
|---|---|---|---|---|
| `logonly` | real obs, **no probes sent** | **11,399** | 7,730 | 0.5% |
| `real0` | real obs, **probes sent** | **7,413** | 4,037 | **22.7%** |
| `derived` | reconstructed obs (+ probes) | 5,282 | 2,517 | 24.5% |
| `keep_capacity` | derived except capacity real | 6,328 (+1,046) | 3,472 | 21.1% |
| `keep_peaceful_at` | derived except peaceful real | 6,033 (+751) | 3,036 | 22.2% |
| `keep_terrain` / `keep_weight` | | 5,220 / 5,319 (±0) | | |

**The probe keystrokes themselves cost 35% and turn 0.5% loopers into 23% — with the policy seeing the true
observation.** That is the stock loop excess (rung-1 census 0.5% vs stock 3.7–12%), and it is not observation content
(D already ruled out the message channel). Reconstruction adds a further −29%; `capacity` and `peaceful_at` are the
largest channels found so far (cast_blocked, path, engraving, hero_tile, inv_state, inv_true still running); a
probe-class ablation (terrain probe / mid-look / extra looks / corridor probe / getpos / all probes off) is queued
behind it. Fixing the probes' side effects is the first lever; `capacity` and `peaceful_at` derivation the second.

Related overnight numbers: rung 2 (non-strict stock, seed 32, died at 7,195 eps with a segfault): 11,555 / 6,722 —
so the strict rules cost little; the loss is reconstruction+probes. One-tree rung 3 with `cant_hold` (seed 21/32,
recovered logs): 10,229 / 5,802 and 10,310 / 5,970, aborts ~5% — **lower than the old-tree rung 3 without `cant_hold`
on the same seed (11,376 / 7,138)**; `r3nch_pkgnle_s406_s21` (same tree, `NH_NO_CANT_HOLD=1`) is running to split
`cant_hold` from the derive delta between the 13:14 box binary and the landed derive. 4B lanes at 1.6B, ETA ~18:00.

## Gotchas that produced the mess

1. **`rc=$?` after `$(date +%T)` is always 0.** 16 drivers use `echo "$(date +%T) ... rc=$?"`; the subshell resets `$?`. Every `rc=0` in `long.log`, `chalcert.log`, `claimcert.log`, `chalcert2b.log` is meaningless. `claim2b_s504` segfaulted (`claim2b.log`); three `claimcert` arms and one `overnight` cert arm segfaulted (all with `NH_STOCK_CLEAREOS=1`). Only `box_certq.sh` and `box_baseline_fork.sh` capture `rc` on its own line. Check `*.driver.log` / `*.log` stderr for `Segmentation fault`.
2. **Three kinds of "score"** — see the table at the top. Never compare across kinds.
3. **`box_attr2.sh` hardcodes seed 7.** Its `_s11` arms are seed 7 duplicates.
4. **Two box trees.** `PufferLib` (pre-package) and `PufferLib_pkg` (claim tree) coexist; certq/attr2 numbers are from the former, everything pkg/claim from the latter.
5. **The local repo is a third tree** with `cant_hold`, which no lane has trained with. Keep it as dev; do not cert on it until a training run is promoted from it.
6. **`cant_hold` was never reset between episodes** (ported 2026-09-11 from `wt_gate`, which had the same omission). Set by "can't even hold anything" / "Don't be ridiculous", cleared only by "You return to…", so a hero that dies polymorphed leaves WIELD/THROW/ENGRAVE masked for every later game in the same process. Every multi-episode CPU-path run from `wt_gate` or the repo before 19:10 carried it (all rung-4 batches; any local vec eval). Fixed in `nethack_do_reset`. Found because rung-4 medians decayed with episode index while one-episode-per-process runs matched rung 3.
7. **Verify on the production path.** The "three byte-identical seeded episodes" check used `nhc_direct.py`, which calls `nhg_zero_state()` and `srand(0)` at every reset and drives `nle.nethack.Nethack` directly; production `nhc_agent.py` does neither and drives the gym env. A verification that passes on a different driver proves nothing about the one that produced the numbers.

## Consolidation — moving everything into this repo (state at 18:45)

The claim tree `PufferLib_pkg` is a checkout of pufferlib **`97416d02`** + 6 hand edits, with an inner
`vendor/fast-nle` at fork commit **`1d7ab70`** + 6 hand edits. `vendor/fast-nle/` is **gitignored by pufferlib**
(`.gitignore:196`): the engine is its own git repo (`FinlaySanders/fast-nle`), so engine changes can only be
tracked there, never by pufferlib's git. Local HEAD is `c7590188` (113 commits past `97416d02`); local inner
engine is `10236329b` (= `1d7ab70` + one "tmp" commit) with 33 dirty + 4 untracked files.

What is now in the repo (this directory):
- `LEDGER.md` — this file.
- `box/` — every box driver (`box_*.sh`, `nh_long.sh`, `nh_panel.sh`, `nh_eval_burnin.sh`), `analyze.py`,
  `trial_args.py`, `rewcoef.py`, the claim hyperparameter config `sweep_1788766770910_1122.ini`, and the
  `pkgnle_s406/407.ini` metric logs. Historical drivers keep their bugs (see Gotchas); `box_baseline_fork*.sh`
  and `box_chalcert_2b_q.sh` are the current-generation ones.
- `results/` — every `.ep` per-episode log (gzipped) and every cert/lane log from the box as of 18:45.

Claim-tree hand edits and whether the repo has them:

| edit | claim tree | repo | note |
|---|---|---|---|
| `fs.h` `NH_NLE_OPTS` / `NH_KEEP_PILELIMIT` | yes | yes | ported earlier |
| `netlib.h` `pile_limit:0` | yes | yes | ported earlier |
| `winrl.cc` four export changes + `you.h`/`engrave.c`/`mon.c` | yes | yes | ported earlier |
| `nethack.h` **public-band hunger gate** (`blstats[HUNGER] >= 3`, was `internal[7] <= 10`) | yes | **ported 18:44** | changes the CAST mask — pending-obs item 1; the claim weights trained WITH it |
| `nethack.h` **`NH_EPLOG` hook** | yes | **ported 18:44** | without it no `.ep` → no cert from the repo; explains why the local "certs" were raw means |
| `nle.c` **public-obs inventory weight** (containers empty, eaten food half) | yes | **ported 18:46** | observation change; the claim weights trained WITH it |
| `do_name.c` **`NLE_GETPOS_NORMAL`** gate | yes | **ported 18:46** | harness/probe support |
| `pufferl.cu` final-eval uses sweep target metric | yes | yes | already at HEAD |
| `drone.h` (+62) | yes | n/a | unrelated to nethack |
| `nethack.h` `cant_hold` | **no** | yes | repo-only; no lane has trained with it |
| `nethack.h` `log.perf` = depth/50 (repo) vs `= score` (claim tree) | differs | differs | metric definition, not a score change; user territory |

Remaining differences after the ports are HEAD-vs-`97416d02` history (`nethack.c` 129 lines, `nethack.h`,
`pufferl.cu` 276, `puffercpu.c` 136, `config/nethack.ini` 44) and the local engine's arena/planes work.
Those are the repo being *newer*, not the repo missing claim-tree edits.

Not moved, and not movable: the 53 GB of checkpoints and the running lanes. The box stays the execution host.
Rule going forward: the box runs a clone of this branch, not a hand-edited snapshot; every lane/cert line logs
`git rev-parse HEAD` + dirty count for both pufferlib and the inner engine. `PufferLib_pkg` stays frozen as the
provenance snapshot for `pkgnle_*` / `claim2b_*`.

### Engine branch (2026-09-11 20:30) — see `ENGINE.txt`

`fast-nle` **`nle-stock` = `dfbdc84c8`** = `1d7ab70` + the training tree's six export edits, copied byte-for-byte
from the box. Golden-trajectory gate (`tests/replay_golden.c`, 34 recorded stock episodes, hash over
glyphs/chars/colors/specials/blstats/message):

| engine | gate | vs training engine (full per-step sequences) |
|---|---|---|
| pristine `1d7ab70` | **34/34** | — |
| box training engine `1d7ab70`+6 (`bdb9896bd881`) | 19/34 — the 15 divergences are the intended export changes | — |
| **`nle-stock` `dfbdc84c8`** | 19/34, same 15 | **identical on 34/34** |
| local perf work (`perf-planes-wip` `c967fcf7c`, was the local `vendor/fast-nle`) | 19/34 | **differs on 3/34**: `hea_seed1006_2013` @140 (wounded-legs timer expires a turn early: "Your leg feels better.", Dex 7→8), `aa_seed7003` @38295, `aa_seed7010` @36010 |

So: the export changes cannot affect score relative to training (same engine); the local pile-plane/track/onscary
perf work **does** change game behaviour and is parked, not shipped. pufferlib has no dependency on it.

## Plan

1. ~~`baseline.log` — rung-1 fork cert of `pkgnle_s406/407`~~ **done 18:39, passed** (see rung-1 table).
2. When `claim2b_s501/502/503` land: rung-1 fork cert on the pkg tree (`box_baseline_fork.sh`, lane param), then the already-queued rung-3 challenge cert.
3. Optional middle rung: non-strict stock cert of `pkgnle_s406` to split reconstruction cost from strict-mode cost. Not launched.
4. Local repo: promote to a training tree only by syncing `ocean/nethack` + `vendor/fast-nle` into a new package build on the box, then a fresh lane; that lane's md5 line becomes the next row here.

## 2026-09-12 morning — results landed, queue changes

**Rung 2, seed 21 (box, one-tree build of ~19:00 09-11 = sticky `cant_hold`, non-strict):** 11,543 eps (12 h timeout, rc=124),
burn-in-adjusted **11,740 (se 162) / 7,178**. With seed 32 (11,555 / 6,722, segv at 7,195) rung 2 pools to ≈ 11.7K / 7.0K.
Caveat: taken with the sticky mask. Non-strict keeps the top line, so the "You return to…" clear is less likely dropped
than in strict mode, but the number is not clean until re-run on `a51b1953`+.

**`r3nch` (box, one-tree `a51b1953`, `NH_NO_CANT_HOLD=1`, strict, seed 21):** first attempt segfaulted after ~100 eps
(07:17, rc=139); `run_r3nch.sh` relaunched it, live on gpu 7. At 6,536 eps (09:22): **11,414 (se 267) / 6,786**, aborts
10.8 %. Same seed: A (sticky) 10,503 / 6,128; old tree (no mask) 11,376 / 7,138; local X1 (no mask) 11,956 / 7,540.
The box reproduces the regression and its cause. Note `NH_STOCK_LITERALOPTS=` (empty) here → backend falls through to
the strict rc path (`if (litopts && *litopts)`), i.e. NLE's option set applied by rc rewriting, not the literal string;
same option set, different delivery.

**Rung 4 Python, 2B `claim2b_s503` (box, tree `91414698` = sticky extended `cant_hold`, `libnhagent` 57e5771fb38a):**
n=480 equal-k: **median 6,414, mean 12,462** (p25 1,692, p75 17,610). Rung 3 old tree `chal2b_s503` = 13,816 / 7,600 →
−16 % median, the size of the sticky penalty (−19 % at 1B). Not a binding loss; re-run on the fixed tree for the claim
table. The "episode 1 vs 2+" split (12,311 vs 5,963 here; 3,640 vs 7,325 for the 1B) points opposite ways on n=24 —
noise, not a cross-episode leak.

**X4 (local, expiring `cant_hold`, strict seed 21) — final, 6,074 eps:** **11,750 (se 306) / 7,199**, aborts 2.5 %. Equal to X1
(no mask, 11,956 / 7,540) within noise, with a quarter of its aborts. E2 (X4 + zero-time v2) started 09:23.

**Corrected ablation (`/tmp/ablate_gp2`, `NLE_GETPOS_NORMAL=1`):** logonly 11,377 (se 234) at 3,012 eps, worst zero-time
run 9,404 steps. `derived` running since 09:12. Made **serial** at 09:20 (second worker stopped by pid, `real0` re-queued
at the front): E2 (11.9 GB) + one harness arm (7.5 GB) fit the 24.5 GB card; two arms + E2 would not, and the memory
gate raced the E2 launcher. ~70 min per arm → 7 arms ≈ 19:00.

**4B lanes at 09:20:** `s601/602` 2.10B, `s603/604` 1.97B (SPS 61–65K) → land ≈ 18:30. `nomask_s607/608` started 09:12,
SPS ~60K → ≈ 03:00 09-13, earlier once the first four free the CPU.

**Box eval queue reordered (09:24):** `launch_r3_4b.sh` (old-4B rung 3 first) and `overnight_extra.sh` waiter B (2B rung 3
after it, mask default) stopped, verified by pid. `equiv/launch_claim_r3.sh`: when gpus 0/7 idle → **one-tree rung 3 of
`claim2b_s503`, seeds 21/32, `NH_NO_CANT_HOLD=1`** (the interface of the old-tree claim certs and the nomask 4B lanes) →
then old-4B `rt_4B_1122_s204` rung 3, same setting. Ends with `CLAIM_R3_CHAIN_DONE`.

## 2026-09-12 10:30–10:50 — E2, r3nch final, claim chain, second box, derive-replay bench

**E2 final (local, strict seed 21, expiring `cant_hold` + zero-time v2):** 6,050 eps, **11,977 (se 313) / 7,354, 0 aborted**
(worst zero-time run 480 steps). X4 (expiring only) 11,750 / 7,199 with 151 aborts; X1 (no mask) 11,956 / 7,540 with 659.
Score neutral, abort class gone → **v2 is the default in the challenge configuration** (`0cf32001`: on when `NH_STOCK_STRICT`
is set; `nhc_agent.py` sets `NH_ZT_MASK=1` for the gym env, which has no strict switch; `NH_ZT_MASK=0` turns it off;
training never sets either).

**`r3nch` final (box, one-tree, `NH_NO_CANT_HOLD=1`, strict seed 21):** 10,067 eps, **11,175 (se 168) / 6,900**, aborted 11.1 %.
Old tree same seed 11,376 / 7,138 (se 170): equal within noise. Sticky A 10,503 / 6,128. Regression cause confirmed on the box.

**Claim chain started 10:26:51** (`launch_claim_r3.sh`): one-tree rung 3 of `claim2b_s503`, seeds 21/32, mask off, tree `a51b1953`,
stock `ce98f220d66f`; 1,220 eps each at 10:45 → lands mid-afternoon. Then old-4B rung 3.

**Second box `cpubox`** (ssh alias; 48-core EPYC 7443, one RTX 3090 24 GB, 503 GB RAM, Ubuntu 24.04, CUDA 12.8): clean clone
of both `nle-stock` branches, stock NLE sources hash-verified (`84c24e5a811b3298`, 537 files), all binaries built after adding
`libomp-18-dev libgl-dev` (missing on the image; the link errors were `-lomp5`, `-lGL`). Fits 3 harness arms / 2 stock evals.
Its log-only reference: **11,841 (se 241)** vs local 11,377 (se 234), same seed → cross-machine scheduling noise ≈ 2 se.
Running since 10:00–10:06: `keep_peaceful_at`, `keep_capacity`, `keep_inv_state`. **ssh refused from ~10:40** (instance down or
rebooting); `/tmp/cpubox_resume.sh` waits for it and then pulls, builds the fixed stock binary + `puffer_nethack_harness_fix`
and queues `after_ablation.sh` (strict canary of the derive fixes, seed 21 6,000, vs E2; harness `derived` with the fixed
derive, vs the local old-derive `derived`). Ablation split: local = `real0`, `keep_hero_tile/cast_blocked/path` (two workers).

### Derive-replay bench (`53d051ea`) — the unit test for the reconstruction
`NH_DERIVE_REC=<dir>` on the fork harness (mode 0) records, per episode, every key the derive saw, every probe reply and the
fork's truth at every hook (`nh_derive_rec.h`, block-delta + gzip, ~2 MB/episode). `nh_derive_replay` re-runs `nh_derive.h`
over the files with no engine; `derive_replay.sh <dir>` runs one file per core and merges. **Validated: the replay reproduces
the live harness table exactly (18 channels, queries and mismatches equal) on 176 episodes, 34 s wall on 32 cores.**
`--watch <channel>` prints every change of the real value with the last messages (how the bugs below were found in minutes).
Limits: a change to *what the derive probes* diverges from the recording from that step on (counted, episode skipped) —
re-record after probing changes, validate them live. The recording carries the `NH_*`/`NLE_*` environment (the derive reads
its switches from it). Corpus: `/tmp/drec` (old derive, seed 99, 128 agents, 48 complete + 128 partial episodes, 340 MB);
`/tmp/drec2` being recorded with the fixed derive.

First corpus, old derive (mismatch per query): capacity **6.69 %**, path 5.23 %, food_underfoot 2.40 % (of 707), weight 1.31 %,
peaceful_at 0.61 %, intrinsics 0.25 %, hero_tile 0.11 %, terrain 0.014 %, spells 0.010 %, everything else ≤ 0.003 %.

Fixes (`0cf32001`) and their effect on that corpus:
| channel | before | after | cause |
|---|---|---|---|
| capacity | 6.689 % | **0.130 %** | "Dumb move!  You strain a muscle." always wounds the right leg (−100 cap for 6–10 turns); the derive only knew xan/land-mine. Its heal clear looked for "somewhat better" (3.4 text); 3.6.6 prints "Your leg feels better." Now: strain / refusal ("in no shape for") / bear trap / xan / land mine set it with the wound's maximum duration as a fallback expiry (the heal line is often lost in a multi-key step). |
| food_underfoot, container_at | 2.405 %, 9 | **0** | the fork scans the whole floor chain; the derive tested only the top object while standing still |
| intrinsics | 0.249 % | **0** (replayable subset) | `dr_parse_self` read the farlook line from its start; the form is inside parentheses (`d   a dog or other canine (werejackal called Agent)`) — it never matched, so `S->form` was always −1. Now parsed, were-forms disambiguated by the line's class letter, resistances of the form from `NHT_MON_MR/M1` (new tables from the nle package, `gen_mon_flags.py`), re-probed after prayer and every 40 turns while polymorphed (the return-to-form line hides in the prayer's pages; without the re-probe the first parser fix made intrinsics 2.8 % and capacity 3.9 % *worse*). |
Left: weight 1.3 % (an unidentified appearance whose true type weighs more — gauntlets of power 30 vs leather gloves 10 — is
unknowable from public text; would need the fork to export appearance-canonical weight), path 5.2 % (BFS shortest path vs the
actual run: the run turns corners orthogonally where BFS cuts the diagonal), peaceful_at 0.6 % (a monster angered between the
farlook and the hook), hero_tile 0.1 %.

**`path` is not an observation channel.** `nle_path_drain` feeds only the first-visit exploration reward
(`nethack_tile_claim`); `stats.visited` is never read into the observation. Its 5.2 % mismatch cannot move a stock eval
(the policy never sees it and rewards do not act at eval time); it only matters for training, which is exact on the fork.
`keep_path` dropped from the ablation; `keep_cast_blocked` dropped too (0 mismatches in 107K queries: identical to `derived`).
Observation channels the policy reads and their residual error after `0cf32001`: peaceful_at 0.66 %, hero_tile 0.22 %,
capacity 0.19 %, intrinsics 0.08 %, weight 1.5 % (hidden information), everything else ≤ 0.02 %.

**Harness `derived` arm (local, old derive, mode 1, seed 21, 3,003 eps): raw mean 5,950 (se 135) vs log-only 11,377 (se 234) = −48 %**,
worst zero-time run 99,996 steps; live mismatch rates in derived mode: capacity 13.0 %, weight 3.2 %, intrinsics 3.0 %,
path 1.8 %, food 1.1 % (errors compound once the policy acts on them). The real stock engine loses 11 % at rung 2 and
~11–15 % at rung 3 with the same derive, so **the fork harness in derived mode is not a faithful proxy for stock
reconstruction** (the derive was written for stock's screen semantics: hero glyph on the hero cell, appearance glyphs;
the fork exports the under-tile and eagerly identity-mapped glyphs). Consequences: `keep_<channel>` arms measure
harness artefacts, not stock costs — `keep_hero_tile` dropped, no more harness score arms; the bench (mode 0 replay)
stays valid for *mismatch rates* on fork trajectories; the stock cost is measured only on the stock engine
(rung 2/3 vs rung 1, and the strict canary). The drone `derived_fix` arm (fixed derive, harness) is left running only
as a paired read on the harness itself.

**`.ep` log extended (11:40):** columns 5–11 = role race gender max_depth last_turn killer_mnum+1 killer_mlevel (first four
unchanged; `analyze.py` and the abort counters read columns 1 and 4). Local stock binary rebuilt; the 2B claim cert on the
current tree (`claim2b_s503_r3_local`, strict seed 21, 10,000 eps, default masks, fixed derive) is queued behind the canary
and will be the first cert with the census columns.

## 2026-09-12 12:37 — canary of the derive fixes (1B `pkgnle_s406`, strict seed 21, 6,008 eps, default masks, tree `0cf32001`+)

**12,785 (se 328) / 8,522, 0 aborted.** Same seed, masks and clock as E2 (old derive): 11,977 (se 313) / 7,354 → **+6.7 % mean,
+15.9 % median** from the reconstruction fixes alone. Against the fork reference (14K cert, seeds 7/11: 13,350 / 8,706):
**−4.2 % mean, −2.1 % median** — inside 5 % on both for the first time. Kept-window shape: p10 880, p25 2,886, p75 17,148,
p90 28,610, max 162,710. Ends: died 85.6 %, poisoned 10.9 %, stoned 2.0 %, starved 1.3 %.
Caveats: one seed, 2,008 kept games (se 2.6 %); the fork reference is another seed and protocol. The same-seed, same-protocol
fork arm (`rung1_s21`) runs next; the 2B cert on the current tree (`claim2b_s503_r3_local`, 10,000 eps) started 12:38.

**Harness `real0` (local, old derive, mode 0 = probes sent, real observation shown, seed 21, 3,018 eps): raw mean 7,173 (se 156)
vs log-only 11,377 (se 234) = −37 %**, worst zero-time run 91,691. On the stock engine probes *plus* reconstruction cost ≤ 4 %
(canary 12,785 vs fork 13,350), so this is a **harness artefact**: the fork harness's probe mechanics perturb the game where
the stock backend's do not (cause unknown; suspects: the out-of-band `nle_obs_refresh` after each probe, fork-side prompt/
occupation handling of probe keys). Together with the −48 % `derived` arm this closes the question: **no harness score arm is
a stock measurement**; the harness is kept for recording (bench) and mismatch tables only. Its old-derive live mismatch table
under probe perturbation: capacity 10.1 %, food_underfoot 32 %, weight 2.5 %, path 2.1 %, intrinsics 1.5 %, peaceful 0.29 %.

## 2026-09-12 12:56 — same-seed, same-protocol fork arm: the 1B stock gap is ≤ 2 %
`rung1_s21` (fork interface, seed 21, 6,049 eps, 512 agents, NLE options): **13,060 (se 333) / 8,618**, would-be aborts 29 (0.5 %).
Canary (stock, challenge rules, fixed derive, same seed/protocol): 12,785 (se 328) / 8,522, 0 aborts → **−2.1 % mean, −1.1 %
median**, 0.6 σ from zero. The 1B policy now scores the same on stock NLE under the challenge's rules as on its training interface.
Bench hygiene: the hero-tile check now mirrors the stock export rule (raw hero glyph while blind/hallucinating/engulfed) — the
channel drops 0.224 % → 0.084 %, the rest is stale pile-order memory. Identity: 1/176 corpus episodes lost the welcome line to
the "Friday the 13th" warning (fork fake calendar); today's stock cert shows all 13 roles evenly, so the new-moon line is harmless;
a Ctrl-X (in the challenge action set) fallback is the fix, deferred.

## 2026-09-12 14:15 — the 2B does not close like the 1B; the loss is in the weapon roles
Old-derive 2B finals (drone, mask off, no guard, 6,000 kept): seed 21 **14,289 (se 233) / 8,160**, seed 32 **13,816 (se 222) / 7,886**,
aborts 11 %. Fixed-derive seed 21 (local, running) tracks the old derive's window within +0.3 % mean / +2.6 % median, 0 aborts.
**Fork reference is now ambiguous**: today's tree, seed 7, 10K kept = **17,159 (se 224) / 10,112** vs the claim tree's cert of the
same weights and seed 16,027 / 9,432 (3.6 σ apart; today's tree carries the expiring form mask, the claim tree had none).
A same-tree same-seed fork arm (seed 21) is running on the drone; the local stock certs are compared to that.
**Per-role medians, fork (today's tree, s7) vs stock (fixed derive, s21, 4,702 kept):** Valkyrie 18,279 → 12,096 (−34 %),
Barbarian 22,500 → 16,839 (−25 %), Caveman −22 %, Rogue −20 %, Ranger −18 %, Archeologist −15 %, Priest −13 %, Samurai −7 %,
Tourist −6 %, Knight −4 %, Healer −4 %, Wizard 0 %, **Monk +7 %**. The loss lives in the weapon-using fighters and is absent for
the Monk and the casters → weapon/inventory verbs on stock. Isolation arms queued locally (seed 21, 6,000, fixed derive):
`claim2b_nomask_s21` (form mask off) and `claim2b_noguard_s21` (zero-time guard off). 2B replay corpora: the short one (185 eps,
~1,500 steps each) shows every observed channel ≤ 0.5 %; a 25-minute corpus is recording for late-game rates.
**2B seed 21, fixed derive + guard, final (14:30): 14,357 (se 232) / 8,398, 0 aborted** vs old derive, mask off, no guard 14,289 / 8,160 (11 % aborts):
+0.5 % / +2.9 %. Same-seed fork (today's tree) reads ~16.8K / 9.7K at 4,131 kept → stock gap ≈ −14 % for the 2B.
**Same-seed fork reference for the 2B (today's tree, seed 21, 6,060 kept): 16,520 (se 266) / 9,839**, would-be aborts 66 (0.7 %).
Stock fixed derive, same seed: 14,357 / 8,398 → **−13.1 % / −14.6 %**. Per-role (both seed 21): Valkyrie −27 %, Barbarian −26 %,
Caveman −24 %, Rogue −19 %, Ranger −13 %, Archeologist −12 %, Knight −7 %, Wizard −5 %, Tourist −3 %, Healer 0, Samurai +3 %,
Priest +4 %, Monk +4 %. Losing roles die 20–25 % earlier in turns at the same depth. Stoning ends 3.5 % of stock games vs 1.3 %
on the fork (poison/starvation unchanged). Isolation arms: guard off (running), form mask off (queued), fork mask off (drone).
**Fork 2B, today's tree, seed 7, form mask OFF (`NH_NO_CANT_HOLD=1`, 10K kept): 16,396 (se 208) / 9,745**, would-be aborts 1.0 %.
Mask ON same tree/seed 17,159 / 10,112 → **the expiring form mask is worth +4.7 % / +3.8 % on the fork for the 2B** (2.5 σ); the claim
tree's 16,027 / 9,432 was a mask-off number and agrees with 16,396 within 1.4 σ. On stock the mask bought ≈ 0 (14,357 with vs
14,289 mask-off old derive) → either it misfires on stock for fighters or the guard costs the 2B; isolation arms running.

## 2026-09-12 15:05 — the 2B's own bugs, from a 611-episode 2B corpus (25 min × 128 envs, 2.16M late-game boundaries)
Late-game (turn ≥ 5,000) error rates with derive v1: **weight 4.9 %**, intrinsics 1.6 %, food_underfoot 0.6 %, hero_tile 0.4 %,
peaceful 0.3 %, shop_price 0.26 %, capacity 0.2 %; **identity wrong in 6 of 611 games (1 %)**.
- **Weight while hallucinating** (`2f302173`): NLE randomises inventory glyphs under hallucination; items whose text does not resolve
  to a name fell back to the glyph → random objects priced into the pack (real 863 vs derived 3,458). Fix: hold the last sighted
  weight while `cond & 0x200`. The recorded game: thousands of mismatches → 0.
- **Identity for one character** (`2f302173`): all six failures were a neutral female gnomish Archeologist — the only welcome line
  longer than 80 columns; it wraps to screen row 1 and the parser read row 0 only. Fix: read rows 0–2.
- Intrinsics 1.6 % late = one-boundary lag on lycanthrope form flips; left.
Guard-off 2B arm (`NH_ZT_MASK=0`): tracking *below* the guard-on cert at equal count (6,330 vs 6,965 at 1,543 games) → the guard
is not the fighters' loss. Binaries rebuilt on both boxes (local stock fe9217042d7f, drone 15c7c2b639c3, libnhagent 453478ee8b06);
canary #2 for the 2B (`canary2_2b_s21`) queued behind the guard-off arm; the corpus replay with v2 runs on the drone.

## 2026-09-12 16:15 — afternoon: 1B ladder closed at rung 4; 2B seed 32; what the 2B corpus really said
**1B Python rung 4 (`r4_pkgnle_s406_fix`, 24 workers × 20 games, libnhagent 067f54d39943, tree 069c1fc4): n=480, median 8,389, mean 12,900**
(p10 912, p90 32,050; the episode-1 median 6,275 is a 24-game sample, not a leak). Same weights, seed 21: fork 13,060 / 8,618, stock rung 3
12,785 / 8,522 → **the 1B ladder is closed at every rung (−1 % to −3 %, inside one se)**.
**2B seed 32, derive v1 + guard (`claim2b_s503_r3_local_s32`, 10,041 eps, 6,041 kept): 14,816 (se 240) / 8,856, 0 aborts** vs the old-derive
mask-off seed 32 13,816 / 7,886 (11 % aborts): +7 % / +12 %. Two stock seeds 14,357 / 8,398 and 14,816 / 8,856; two fork seeds 16,520 / 9,839
and 17,159 / 10,112 → **2B stock gap ≈ −13 % / −13 %**.
**Guard-off 2B (`claim2b_noguard_s21`, NH_ZT_MASK=0) at 5,592 games (1,592 kept): 13,990 / 8,227 vs guard-on 14,959 / 8,938 at the same count,
63 aborts vs 0 → the guard stays; it is not the fighters' loss** (final line in /tmp/reg/log).
**Derive v2 replay of the 611-episode 2B corpus: every channel byte-identical to v1** (weight 120,493 → 120,499 of 4.18M queries; identity 6 → 6).
The 15:29 DONE line was wrong — it re-read the v1 output directories; the v2 outputs are `replay_v2*`. Neither 15:05 diagnosis was right:
- **Identity (6/611, every one a neutral female gnomish Archeologist):** not a wrap onto row 1. The welcome line is exactly 80 columns; tty's
  `update_topl` splits it by overwriting the space before "Archeologist." with `\n`, and the message buffer carries that newline. The tokenizer
  stopped at spaces and periods only, so the third word was "gnomish\n" → no race match → male human by default. Fix `5ee2c435`: newlines are
  spaces (plus a --More-- strip and a cut-line rule). **1B corpus identity 1 → 0 of 176 (the Friday-13th game included); the six 2B games 6 → 0.**
- **Weight (2.9 % of boundaries, 4.9 % late; single games wrong on every late step):** not hallucination. Watch traces: "a pair of jungle boots"
  real +50 derived +15, "a pair of old gloves" +30 vs +10, "buckled boots" +20 vs +50 — **unidentified shuffled armour is priced by the
  appearance's default type.** The fork's `nle_weight` sums `objects[otyp].oc_weight`, the true type's weight, for every item identified or not.
  Stock NLE hides the true type as well: `winrl.cc` wraps every inventory and map glyph in `shuffled_glyph` (my reading of `display.h` alone was
  wrong; the bench is faithful here). So **the weight channel is not derivable from anything public** for unidentified boots (15/20/50), gloves
  (10/30), helmets (30/50) and gray stones (10/500); cloaks, potions, scrolls, wands, rings, amulets are uniform within their appearance groups.
  **Measured on stock** (`NH_STOCK_WTCHECK`: walks the stock engine's `invent` with the fork's formula, slot layout verified letter/class by slot;
  128 agents, 208 early games, 525K boundaries): **weight mismatch 5.5 %, capacity 0.15 %**. Fighters pick up armour, casters do not — the
  2B's per-role split — so this is the lead hypothesis, under direct test:
  - drone gpu 7 `stock_wtreal_s21`: stock strict, seed 21, 6,000, **the engine's weight/capacity fed to the policy** (`NH_STOCK_WTREAL=1`, a
    rung-2 crutch, never a cert). Pairs with the local `canary3_2b_s21` (same tree and seed, derived weight): the difference is the weight
    channel's cost on stock.
  - drone gpu 0 `hw_real0_s21` vs `hw_wder_s21`: fork engine, harness mode 0 (all real) vs mode 1 with every channel real except weight.
  If weight carries the loss, the fix is on the fork side (export an appearance-canonical weight and train on it); nothing trained before
  Monday can have it, so the 2B/4B claim carries it as a documented residual.
- Intrinsics 1.6 % late: one missed "You feel healthy." (poison resistance from a corpse; the message fell behind a --More-- in the fork
  recording) → mismatched for the remaining 23K steps of that game. No probe shows intrinsics; left.
**Queue:** the `canary2_2b_s21` waiter was killed before it started; **`canary3_2b_s21` (tree 5ee2c435, stock 452e91f52153: identity newline fix +
weight hold under hallucination) started 16:01** beside the guard-off arm; `claim2b_nomask_s21` (NH_NO_CANT_HOLD=1, derive v3) queued behind the
guard-off pid. Drone stock 52336c7a6585 (3b44bca3), local libnhagent bf00d5903920. 4B lanes at 16:00: s601/602 3.4B, s603/604 3.3B (SPS 56–60K,
land ≈ 18:15–18:50), nomask s607/608 1.3–1.4B (≈ 02:45 Sunday). Rolling panel scores 15–23K (noise ±1K, not results).
