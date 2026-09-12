# NetHack on stock NLE — status, 2026-09-12 15:05

Companion to `LEDGER.md` (every number with its arm name, tree and interface) and `ENGINE.txt` (engine pin).
This is the narrative: the goal, what is established, what is running, what comes next.

## 1. Goal

Train on the fast fork engine, evaluate on **unmodified stock NLE through the real `NetHackChallenge-v0`
environment**, get the same result — and claim a score against AutoAscend (2021 NetHack Challenge winner,
**median 5,300** over a 4,096-episode test phase; ranking = ascensions, then median, then mean).

## 2. The setup, as it stands

**One tree.** Branch `nle-stock` in both repos — pufferlib `d2200ec6`+, fast-nle `dfbdc84c8` — cloned on the box at
`/workspace/pufferlib`, identical locally. The engine is byte-identical to the one that trained every weight we cert
(34/34 golden sequences). `PufferLib_pkg` on the box stays frozen as the provenance snapshot for the 1B/2B claim
weights. Stock NLE sources are untouched (`84c24e5a811b3298`, both machines).

**The interface ladder** (all rungs present NLE's own C API; rungs 2–3 are for testing, rung 4 is the claim):

| rung | engine | observation | rules | role |
|---|---|---|---|---|
| 1 | fork | fork's exports (exact) | ours | training interface; the policy's true strength |
| 2 | stock `libnethack.so` (dlopened per env) | reconstructed from the public screen by probe keystrokes | ours (no abort rule, crutches on) | reconstruction cost in isolation |
| 3 | stock | reconstructed, crutches off | **the challenge's**: NLE option set, 10K no-progress abort, 1e6 cap, real clock | 3× faster proxy for rung 4 |
| 4 | stock inside the real gym env, Python, `reset`/`step` only | same reconstruction | the challenge's, enforced by NLE | **the claimable number** |

Rung 3 and rung 4 are proven identical (byte-identical key streams under a frozen clock; live numbers agree at 1B,
and at 2B once the mask penalty below is accounted for).

**Test bench:** golden-trajectory replay gate for the engine; per-episode `.ep` logs with burn-in-adjusted analysis
(the only kind of number that is a cert); a fork harness with per-channel derived/real switching (`NH_DERIVE_REAL`)
for reconstruction ablations; loop censuses (`NH_STOCK_WEDGELOG`, `.ep` worst zero-time run); and, since 10:30, the
**derive-replay bench**: the harness records every key, probe reply and hook truth (`NH_DERIVE_REC`), and
`derive_replay.sh <dir>` re-runs the reconstruction offline in ~30 s with per-channel mismatch rates, examples and a
baseline diff. It reproduces the live table exactly. A derive fix is now a minutes-long loop instead of an hour-long eval.

## 3. Results

### 3.1 Training side (rung 1, fork), claim configuration (`t1122` hypers + NLE default options)

| training | weights | fork cert mean / median | notes |
|---|---|---|---|
| 1B | `pkgnle_s406`, `_s407` | 13,350 / 8,706 · 13,260 / 8,634 · 13,542 / 8,238 · 13,264 / 8,072 | reproduce the panel finals (13,415 / 13,260): tree, weights, protocol coherent |
| 2B | `claim2b_s501/502/503` | 16,440 / 9,922 · 16,795 / 10,248 · 16,027 / 9,432 | panel finals 15,977 / 16,618 / 16,579 |
| 4B (old config) | `rt_4B_1122` ×4 | panel mean 18,155 | median saturates ~9.5–10K from 2B on |

The stock-conformance changes (export changes, NLE options, pile_limit, hunger gate) are **free once trained on**:
1B lanes with and without them sit inside one seed spread (12.7–13.4K); imposing the new export on old weights at
eval time costs ~4 % (16,200 → 15,500) and retraining recovers it.

### 3.2 Stock (rung 3, challenge configuration) — the claim numbers

| weights | mean | median | aborted | vs AutoAscend median |
|---|---|---|---|---|
| 1B `pkgnle_s406` (4 arms, old tree, no form mask) | 11.2–11.5K | **6.8–7.3K** | 11–14 % | +30–38 % |
| 2B `claim2b_s503` (old tree) | 13,816 | **7,600** | 11.8 % | +43 % |
| 2B `claim2b_s502` (89 % complete) | ~12.8K | ~7.4K | 14 % | |
| 2B `claim2b_s501` (86 % complete) | ~13.0K | ~6.9K | 17 % | |
| 1.57B `claim2b_s504` (lane segfaulted) | 11,811 | 6,957 | 15 % | |

**Rung 4 (real Python env):** 1B median **7,033** (n=480, box) and 8,270 (n=320, local) — in line with rung 3.
2B `claim2b_s503`: median **6,414**, mean 12,462 (n=480), run on the tree with the sticky mask (§3.4), so −16 %
median vs its rung 3 is the mask penalty, not the binding. Re-run on the fixed tree queued (§4).

### 3.3 The interface cost, decomposed (1B, seed 21 where paired)

```
rung 1  13.3K / 8.7K
   -11 % / -15 %   reconstruction + probes            <- the loss lives here
rung 2  11.7K / 7.0K   (two seeds; taken with the sticky mask, non-strict — see caveat in LEDGER)
   ~ 0             challenge rules (abort, NLE options): X1 strict no-mask 11,956 / 7,540 ≈ rung 2
rung 3  11.4–12.0K / 6.8–7.5K   (no form mask: old tree 11,376 / 7,138, box r3nch 11,414 / 6,786, local X1 11,956 / 7,540)
     0             Python binding
rung 4  ≈ rung 3
```

Eliminated as causes: the challenge rules, the abort rule specifically (arithmetic caps it at 2–5 %; masks that removed
aborts did not move the score), the message channel (arm D), the Python binding.
Established: the stock interface makes the policy loop ~7× more often than the fork under identical masks — a
*symptom* of the reconstruction+probes layer. The split inside that layer (probe side-effects vs which channels) is the
corrected ablation now running; the overnight one ran without `NLE_GETPOS_NORMAL=1` and is retracted.

### 3.3b What the bench found in its first hour

On the old derive: capacity wrong on 6.7 % of steps, path 5.2 %, food underfoot 2.4 %, weight 1.3 %, peaceful 0.6 %,
intrinsics 0.25 %; everything else under 0.02 %. Three fixed the same morning (commit `0cf32001`), verified on the corpus:

- **capacity 6.7 % → 0.13 %.** "Dumb move! You strain a muscle." wounds a leg for up to 10 turns (−100 capacity); the derive
  never knew, and its heal message was the NetHack 3.4 text. Kick refusals and bear traps now count too, with a duration expiry.
- **food / containers underfoot → 0.** The fork scans the whole floor pile; the derive looked at the top object only.
- **intrinsics → 0.** The polymorph-form parser never matched (the form is in parentheses in the farlook line), so form
  resistances were never applied. Fixed, plus a re-probe after prayer, which is where the return-to-form line gets lost.

Still open: weight (an unidentified item's true weight is not public), peaceful transitions, hero tile. (`path` turned out
to feed only the exploration reward, never the observation; irrelevant to eval.)

**The 2B is a different story (afternoon).** Same seed, same tree: fork 16,520 / 9,839 vs stock 14,357 / 8,398 (−13 % / −15 %);
the 1B's fixes moved it under 1 %. The loss is in the weapon-using fighters (Valkyrie −27 %, Barbarian −26 %, Caveman −24 %),
who die 20–25 % earlier in turns; Monk, casters and Samurai are at parity; stoning deaths 3.5 % vs 1.3 %. A corpus recorded with
the 2B itself found two more bugs the 1B never triggered: weight goes wild while hallucinating (random inventory glyphs priced as
boulders), and one identity (neutral female gnomish Archeologist) never parsed because its welcome line wraps. Both fixed; the
second 2B canary runs at ~16:20. The zero-time guard is not the cause (guard-off arm reads lower). Two fork certs of the 2B also
disagreed by 7 %; that was the form mask, which is worth +4.7 % on the fork where messages are exact.

**The live effect for the 1B (canary, 12:37): 12,785 / 8,522 with 0 aborts** against E2's 11,977 / 7,354 on the same seed, masks and
clock — +6.7 % mean, +15.9 % median from the reconstruction fixes alone, and −4.2 % / −2.1 % against the fork reference:
inside 5 % on both for the first time. **Same seed and protocol on the fork (12:56): 13,060 / 8,618 → the stock gap is −2.1 % mean,
−1.1 % median, within noise.** The 2B cert on the current tree lands ~14:30.

### 3.4 The cert regression: found, explained, fixed

One-tree rung 3 was ~10 % below the old-tree rung 3 on the same seed. Everything was ruled out byte-for-byte
(derive/backend/tables, build flags, switch sets, upstream env drift) until the paired arm landed:

| same weights, seed 21, strict | mean | median | aborted |
|---|---|---|---|
| sticky `cant_hold` (shipped 09-11), local | 10,503 | 6,128 | 3.7 % |
| **no `cant_hold`**, local X1 | **11,956** | **7,540** | 11.1 % |
| no `cant_hold`, box r3nch (final, 10,067 eps) | 11,175 | 6,900 | 11.1 % |
| expiring `cant_hold` (100 turns; now the default), local X4 (final, 6,074 eps) | 11,750 | 7,199 | 2.5 % |

Mechanism: the flag is set soundly (every engine site is a form test) but was cleared only by "You return to…",
which stock's message channel can drop; a de-polymorphed hero then kept four verbs masked for the rest of the game.
Fork side unaffected (rung 1 equal across trees; fork loop census 0.42 %). Fix `a51b1953`. Every one-tree stock
number taken before it carries the penalty: rung 2 both seeds, the 2B Python rung 4, the box `r3_*` arms.

### 3.5 Masks (stock effect, strict, seed 21, 6,000 paired episodes)

| mask | effect | status |
|---|---|---|
| extended `cant_hold` (+WEAR, +2 refusal texts) | aborts 3.7 → 1.5 %, score neutral (P = 0.51) | in tree, now expiring |
| zero-time memory v1 (mask on first free repeat) | aborts → 1.6 %, **score −8 %** (fast heroes' extra actions read as refusals) | opt-in only |
| **zero-time memory v2** (mask on the *second* identical free repeat) | E2 on the expiring mask: **11,977 / 7,354, 0 aborts in 6,050** vs 11,750 / 7,199 with 151 | **default in the challenge configuration** (`NH_STOCK_STRICT`, and `nhc_agent.py`); `NH_ZT_MASK=0` off |

## 4. Running now

**Box (8 GPUs, CPU-saturated by six trainers):**
- **4B `nlestock4b_s601–604`** — sticky-`cant_hold` interface, at 1.97–2.10B steps, SPS 61–65K → land ≈ 18:30.
- **4B `nlestock4b_nomask_s607/608`** — **no form mask at all** (user's call), started 09:12, SPS ~60K → ≈ 03:00 09-13,
  earlier once the first four finish. The 4-vs-2 comparison measures the training-side cost of the mask directly.
- gpus 0/7 since 10:27: **one-tree rung 3 of the 2B `claim2b_s503`, seeds 21/32, mask off** — the claim re-run
  (1,200 eps each at 10:45, lands mid-afternoon) → then the old 4B `rt_4B_1122_s204` on rung 3.

**Second box `cpubox`** (48 cores, one 3090; brought up 09:35–10:00): `keep_peaceful_at`, `keep_capacity`, `keep_inv_state`
running since 10:00; then the strict canary of the derive fixes (seed 21, 6,000, vs E2) and a fixed-derive `derived` arm.
**ssh refused since ~10:40** — a resume script waits for it.

**Local (4090):**
- E2 done (§3.5). `derived` (old derive) at 2,300 / 3,000, `real0` (mismatch table live) running; then `keep_hero_tile`,
  `keep_cast_blocked`, `keep_path`. Re-recording the replay corpus with the fixed derive.

## 5. Next

1. **Canary of the derive fixes** (second box): strict seed 21 vs E2's 11,977 / 7,354. Same masks, only the derive changed.
2. **Ablation arms** → which channels move the score; the bench then names the mechanism for each in minutes.
   Next bench targets: path (orthogonal-preferring run reconstruction), peaceful transitions, then a fork export of
   appearance-canonical weight if weight turns out to matter.
3. **Claim table on the fixed tree**: 2B rung 3 (queued), then Python rung 4 of the 2B, both with the mask decision applied.
4. **4B certs** (rung 1 → 3 → 4) when the lanes land; the 4-vs-2 groups settle the mask question for training.
5. Reconstruction engineering in the order the ablation names: capacity, peaceful_at, inv_state / inv_true (the
   mask inputs the fork gets from engine hooks), then probe laziness (fewer keystrokes per step also halves cert time).

## 6. Things that bit us, now guarded

- Three kinds of "score" (panel rolling final, raw CUDA_EVAL mean, burn-in-adjusted cert) — only the last is a cert.
- `echo "$(date) rc=$?"` always prints 0 — every old driver's `rc=0` was meaningless; new drivers capture `rc` first.
- A "killed" waiter that was not (fired 90 min later, reset live logs) — kills verified by PID re-listing; logs recovered via `/proc/<pid>/fd`.
- Side builds linking the scratchpad's engine (twice) — build scripts now fail on the wrong library.
- Harness without `NLE_GETPOS_NORMAL=1` — invalid ablation, retracted; the driver sets it.
- Per-index medians at n=16–24 swing 3–15K by chance — only equal-k pooled numbers are readable.
- Two 512-agent stock evals plus a harness arm do not fit the 4090; memory gates race launchers — one queue per GPU.
- A sticky belief on a droppable message channel — §3.4.
