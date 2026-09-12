# NetHack on stock NLE — status, 2026-09-12 09:50

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
for reconstruction ablations; loop censuses (`NH_STOCK_WEDGELOG`, `.ep` worst zero-time run).

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

### 3.4 The cert regression: found, explained, fixed

One-tree rung 3 was ~10 % below the old-tree rung 3 on the same seed. Everything was ruled out byte-for-byte
(derive/backend/tables, build flags, switch sets, upstream env drift) until the paired arm landed:

| same weights, seed 21, strict | mean | median | aborted |
|---|---|---|---|
| sticky `cant_hold` (shipped 09-11), local | 10,503 | 6,128 | 3.7 % |
| **no `cant_hold`**, local X1 | **11,956** | **7,540** | 11.1 % |
| no `cant_hold`, box r3nch (6,536 eps, live) | 11,414 | 6,786 | 10.8 % |
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
| **zero-time memory v2** (mask on the *second* identical free repeat) | **1 abort in 6,062**, score neutral (P = 0.50) | opt-in; E2 decides default |

## 4. Running now

**Box (8 GPUs, CPU-saturated by six trainers):**
- **4B `nlestock4b_s601–604`** — sticky-`cant_hold` interface, at 1.97–2.10B steps, SPS 61–65K → land ≈ 18:30.
- **4B `nlestock4b_nomask_s607/608`** — **no form mask at all** (user's call), started 09:12, SPS ~60K → ≈ 03:00 09-13,
  earlier once the first four finish. The 4-vs-2 comparison measures the training-side cost of the mask directly.
- gpu 7: `r3nch` (one-tree rung 3, mask off, seed 21) to 10,000 eps, ≈ 10:30.
- then (`launch_claim_r3.sh`, gpus 0/7): **one-tree rung 3 of the 2B `claim2b_s503`, seeds 21/32, mask off** — the
  claim re-run (~12 h) → then the old 4B `rt_4B_1122_s204` on rung 3 (what a 4B does on stock today).

**Local (4090):**
- X4 done (expiring mask = no-mask score within noise, a quarter of the aborts); **E2** (v2 mask on top of it) running since 09:23, ≈ 12:30 — decides the default eval mask set.
- corrected reconstruction ablation, serial: `derived` running, then `real0`, then keep_peaceful_at / capacity / inv_state / hero_tile / cast_blocked / path (~70 min each, ≈ 19:00).

## 5. Next

1. **E2** → if neutral-or-better with ~0 aborts, v2 becomes the default stock-side loop guard.
2. **Corrected ablation** → probes vs channels split; each named channel is a derive fix with a one-arm re-test
   (~1 h a cycle), gated by the replay gate and a **fixed-seed rung-3 canary** (would have caught §3.4 a day
   earlier; to be added next to the golden gate).
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
