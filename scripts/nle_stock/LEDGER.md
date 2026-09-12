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
