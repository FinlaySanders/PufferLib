# Article plan — NetHack, from PufferLib to stock NLE (draft Sat 2026-09-12, due Mon 2026-09-14)

Working title options: *"A neural NetHack agent that out-scores AutoAscend on the challenge interface"* /
*"What it took to train NetHack end-to-end: engine, interface, reconstruction"*.
Companion files: `STATUS.md` (current state), `LEDGER.md` (every number with provenance), memory notes per campaign.

## 0. The claim we can make, and the one we cannot

**Reference:** AutoAscend, NeurIPS 2021 NetHack Challenge winner, symbolic. Final phase: 4,096 episodes, random
role/race/alignment/gender, no seed control, the environment's own 10,000-step no-progress rule.
Its median: **5,336.5** (challenge leaderboard; "~5,300" in the report). Later independent re-evaluation (Piterbarg et al.
2023, "NetHack is Hard to Hack", Table 2): mean 8,556 ± 187, median 4,918. The best neural entries of the challenge were
~3× lower in median and ~5× lower in mean; the best neural model of that 2023 paper: median 972, mean 1,551.
No agent in the challenge ascended (half a million games), and neither does ours.

**What we have today (burn-in-adjusted, 10,000 kept episodes each unless noted):**

| interface | 1B (`pkgnle_s406`) | 2B (`claim2b_s503`) | 4B |
|---|---|---|---|
| training interface (fork engine) mean / median | 13,350 / 8,706 | 16,027 / 9,432 | panel mean 18,155 (old config); new lanes land tonight |
| stock NLE, challenge rules, C harness (rung 3) | 11.2–11.5K / **6.8–7.3K** | 13,816 / **7,600** | Sunday |
| real `NetHackChallenge-v0`, Python, reset/step only (rung 4) | median **7,033** (n=480) | re-run on the fixed tree Sunday | Sunday (best lane only) |

So the honest headline today: **a single policy, all 13 roles, evaluated on the genuine challenge environment under
the challenge's rules, with a median of ~7,000–7,600 against AutoAscend's 5,336 (+30–43 %)**, and means ~11–14K
against 8.5K. Every number in the article comes from a logged run with tree SHA, engine SHA, weights md5 and seed
(`LEDGER.md`); the eval protocol (512 agents, burn-in 4,000, 10,000 kept) is stated once.

**Caveats to state plainly:** (1) our 4,096-episode-equivalent is 10,000 episodes at eval time, not a hidden test
set; (2) 11–14 % of stock games end by the no-progress abort (the loop guard just landed and takes that to ~0 — the
fixed-tree numbers Sunday replace these); (3) NetHack reads the wall clock (moon phase → Luck): all our certs ran on
new-moon days, AutoAscend's date is unknown; (4) the policy was trained with an exploration reward and a 10K-step
episode cap — the cap matches the challenge's no-progress rule only loosely.

**Results still to land for Monday (all queued):**
- today 12:15 — strict canary of the reconstruction fixes (seed 21) vs E2: does fixing the derive move the score?
- today ~15:00 — 2B rung 3 on the fixed tree, seeds 21/32 (the claim-table 2B, mask off)
- tonight — 4B lanes `s601–604` (18:30) and `nomask_s607/608` (~03:00)
- Sunday 06:00–10:00 — rung 1 certs of all six 4B lanes (fork, 20 min each, 6 GPUs)
- Sunday 10:00–16:00 — rung 3 (stock) for the two best 4B lanes, seeds 21/32; rung 4 Python for the best lane
- Sunday — behaviour census on the final weights (per-role medians, death causes, verb economy, depth, farming share);
  the `.ep` cert log now carries role / race / gender / max depth / last turn / killer per episode (from 11:40 09-12), so
  every cert from here on doubles as a behaviour census
- **Do not plan on harness `keep_<channel>` score arms**: the fork harness in derived mode loses 48 % where the stock engine
  loses 11 % (it was written for stock screen semantics) — stock costs are measured on the stock engine only

## 1. Opening: the result (≈ 1 screen)

- One figure: score distributions (log-x) for ours-on-challenge-env vs AutoAscend's median line; medians labelled.
- One table: the ladder above, three interfaces, 1B / 2B / 4B.
- One sentence on scale: a single 1024-wide, 4-layer policy with a MinGRU, trained 1B–4B steps at ~330K steps/s on
  one GPU box; eval on the challenge env is ~1,000 episodes per CPU-hour.
- The two-line story: *training end-to-end works if the environment is fast enough to run billions of steps, and
  the hard part of claiming a number is making a fork-trained policy see the same world on the stock interface.*

## 2. What the policy does (behaviour breakdown, ≈ 1 screen + 2 figures)

Material already measured (re-run on the final weights Sunday):
- **Per-role medians** (pet study, t1122 2B): Monk ~17–21K, Rogue/Ranger ~9–11K, others 8–12K; role is the largest
  single factor. Figure: per-role box plot.
- **Death anatomy** (19,070 deaths census): 87 % combat, 20 % non-monster (traps/poison); killers soldier ant, dwarf,
  Woodland-elf, hill orc at dlvl 2–5; food clock: fainting share of deaths 0.2 % → 36 % with game length in the
  1B era, then **starvation solved (<1 % of deaths)** once the food economy was learned (rations 52 %, lichen 15 %).
- **Verb economy**: throws, wears, engraves (Elbereth ~9/ep), zaps, casts; the Ranger fires its bow 168 times/ep
  with zero launcher-specific bits in the observation (learned bow↔ammo from raw identity).
- **Two attractors**: farming (spawn-camp on dlvl 1–2, ride the step cap) vs diving; seed decides the basin; diving
  out-scores farming by ~14 %; the stair mask (+522) converted farmers to divers.
- **Tempo lottery**: within a config the score spread is explained by tempo (valid moves, throws, eats, game time),
  not by verb richness; waste steps (moving into walls, hunger-refusal spam) were 18–37 % of all steps before masks.
- **Consolidation squeeze**: at 20–44M steps every run suppresses the delayed-payoff verbs (throw/wear/cast/engrave/
  drop/pray) to <35 % of their final rate, then they come back as competence crystallises; severity does not predict
  the final score.
- **What the representation encodes follows demand**: the same encoder learns downstairs direction to R² 0.995 in a
  digging policy and 0.03 in a merchant policy (double dissociation); "the encoder can't see X" was never the answer.
- **Pets**: every role abandons the pet by turn ~1,000; pets cause dlvl 1↔2 stair yo-yo (Healer 11.5 vs 1.7 descents)
  and buy no score.

## 3. The body — story arcs (pick 4–5 for a short article; the rest become a "notes" appendix or a second post)

### A. Getting NetHack to run at RL speed (engine)
- NLE's C engine, vendored as **fast-nle**: per-env bump arena (free is a no-op, episode end unmaps), fcontext
  coroutines, one process, 32 threads; the Python layer is gone, the env talks to the engine through NLE's own C API.
- **Bugs found on the way** (all deterministic repros, all fixed in the fork): global-dynamic TLS + coroutines +
  thread migration corrupted envs across threads (the sweep-killer); `getenv` inside the RNG accounted for **45 % of all
  engine instructions**; NetHack's panic() ran an emergency save on half-restored state and segfaulted; `sysopt` freed
  once per process from every thread (double free at 4+ threads); `nle_end` used the calling thread's stale context.
- Numbers: engine 2.1–2.4× faster than vendored NLE at equal behaviour; training **294K → 333K steps/s**; later
  campaign to 1.32× bit-exact engine + rollout scheduling; **every engine change gated by 34 golden trajectories**
  (byte-identical glyphs/chars/colors/blstats/messages vs recorded stock episodes).
- Wall clock: NetHack reads time() for moon phase, night, Friday 13th and the birth timestamp, which leaks into
  shopkeeper names, price parity, scroll labels; the fork derives the date from the seed → games reproduce from seeds.

#### A2. The determinism hunt (one afternoon, 2026-07-08, 35 commits on `msan-hunt`) — a self-contained story
- Symptom: "transient observation noise" — identical seeds, occasionally different games. First hypothesis: an
  uninitialised read. MemorySanitizer certified every observation byte initialised across 91K deep steps *while 13
  hash flickers happened in the same run* → the mechanism was address-dependent **initialised** data.
- First divergent message: a shopkeeper's greeting. A time-sweep proved the divergence tracks `ubirthday/257`:
  NetHack buckets the birth timestamp into the shopkeeper-name index, and when the index overflows the list an extra
  `rn2()` shifts the whole RNG stream. Three more upstream leaks fell out of the same gate: a `#if MACOSX` branch in
  `eat.c` that draws RNG on one platform only; ~15 call sites with RNG draws in unspecified argument-evaluation order
  (gcc -O3 and clang disagree, invisible to every sanitizer); `qsort` tie order in `sort_rooms` (glibc vs macOS libc →
  a doorway exists on one platform and not the other). All fixed; goldens now replay identically at clang -O2 and
  gcc -O3, on Linux and macOS, under a frozen or seed-derived clock.
- Then the self-inflicted one: the per-draw RNG tracer added for the hunt did a `getenv` per random number — 45 % of
  all engine instructions. Removing it was the largest single speedup of the project.
- Stock NetHack 3.6.6 bugs found by running billions of steps under sanitizers: three use-after-frees (killing an
  engulfer on a level-teleport trap; a shapeshifter expelled onto one; a pet relocated mid-move leaving a stale grid
  pointer — "~15 % of long RL runs died to this"), an infinite loop in `alter_cost` (shopkeeper scan restarts at the
  same shopkeeper), a missing guard in `tended_shop`, an out-of-bounds read in `boomhit`.
- Framing number: the fork is ~16,500 lines of real change in 42 gated commits, and 289,000 lines of recorded golden
  corpus — **the proof apparatus outweighs the code 20:1**, with five CI oracles (writable-section check; golden replay
  sequential / interleaved / thread-shuffled; wall-clock independence; -O3 independence; blstats parity).
- Version note for accuracy: the training engine is NLE's tree of June 2026 (NetHack 3.6.6 with the 3.6.7 patch);
  the stock evaluation env is NLE 0.9.0. Say "NetHack 3.6" in prose.

### B. What the agent sees (observation + encoder)
- Full 79×21 glyph map (map memory included) + 27 status values + inventory (glyph, letters, class, an 8-int8
  per-slot *item state* gated on what `doname` would print — no identity leak) + the top-line message.
- **Fair observation**: shuffled appearances, not true identities (fixed an NLE leak where object glyphs exposed
  identity); erosion bits doubled as "rotten" storage for food and leaked — found by a 100K-step invariance probe.
- Encoder: factorized glyph embedding (kind + species; +12 % paired, pets/detected/corpses share species content),
  9×9 egocentric patch + patch-max global branch (sum branch collapsed on some seeds), inventory keys, message as a
  **character-trigram bag** (+14 % across 4 seeds; the only channel carrying event feedback), ratio features (hp/hpmax:
  +364 on its own). Architecture sweeps were null within seed noise; every win came from behavioural diffs.
- Determinism: bit-reproducible training (oracle hashes), gradient checks against float64 torch for every kernel.

### C. How it acts (action space + decoder)
- 19 heads: verb (22) + 12 per-verb item-slot heads (55) + 6 per-verb direction heads (8). Macros turn one decision
  into NetHack's multi-key dialogue (Elbereth = 'E', '-', wipe-confirm, text; count-prefixed search `20s`).
- Masks only for legality (a mask on a valid action is strategy shaping; the full-HP REST mask was removed);
  **delayed-payoff verbs are absorbing states for policy gradient** (a verb that pays 50 steps later dies before it
  pays) → an ε-floor per verb and head gating.
- Pointer decoder v3: five per-verb cosine queries over inventory keys, learnable temperature; slot identity is
  position-invariant so no inventory canonicalisation.
- Trainer landmines found: `NUM_ATNS` stride aliasing actions across envs; per-head stack arrays sized 16;
  bf16 parameter alignment (every tensor numel % 8 or the checkpoint silently shifts); decoder weight struct aliasing
  made the sampler continuous; rewards hard-clamped to [−1, 1] (70 % of positive reward mass was clipped — several
  "flat" reward terms were arithmetically invisible); an upstream hoist that killed the V-trace correction.

### D. Reward
- Score-equivalent decomposition of NetHack's own score (4×exp per kill + gold + 50×depth), plus an exploration
  (scout) term; reward scale is not a gentleness knob (advantages are normalised per minibatch).
- Pruned from 12 to 7 terms by paired knockouts: exp is the keystone (−4,578 without it), the rest null within
  a ±400 seed band; depth-delta beat per-floor payment (the latter created a farmer/explorer bimodality).
- Farming is legitimate under the score objective; the article should say so and show both attractors.

### E. Scale
- 250M → 1B → 2B → 4B: 1B mean 12,957 (t1122 config), 2B 16,702 (+29 %), 4B 18,155 (+9 %); medians saturate
  ~9.5–10K from 2B; an earlier config family bent between 1B and 2B ("train longer" is not a free lever).
- Swept hyper-parameters (Protein), never hand-edited; every run ends with a free 10K-episode eval that feeds the sweep.
- Eval protocol lessons: rolling training scores are ±1,000 noise; cold-start censoring; burn-in 4,000; ε pinned to 0;
  per-index medians at n=16 swing 3–15K.

### F. Making it real: the stock-NLE ladder (the second half of the article)
- Why: the fork's 13 introspection hooks and export changes are not available on stock NLE; a claim on the
  challenge interface needs the policy to see the same world from **the public observation only**.
- **Reconstruction** (`nh_derive.h`, ~1,300 lines): terrain under the hero from `#terrain`, peacefuls from farlook,
  spells from `+`, discoveries from `\`, weight/capacity from inventory text and status, wounded legs / intrinsics /
  polymorph form from messages, engraving state from what the hero wrote and read. ~10 probe keystrokes per decision.
- **The ladder**: fork interface → stock engine + our rules → stock + challenge rules → the real gym env in Python.
  Rung 3 ≡ rung 4 byte-for-byte under a frozen clock.
- What the interface costs and why: rung 1 → 2: −11 % mean / −15 % median (reconstruction + probes); challenge rules
  and the Python binding: ~0. The stock interface made the policy loop 7× more often (zero-time refusals repeated
  until the no-progress rule fired).
- **Building the real binding found four bugs the harness hid**: the gym reset() eats the welcome line (identity was
  always Archeologist), Enter arrives as CR not LF (550 cancelled prompts per game), a 1,000-key stall cap, terrain
  probe off.
- **A certification regression and its cause**: a form belief set from refusal messages and cleared by one message
  that the stock channel drops — 12 %/19 % of score; found by paired arms in a morning; fixed with an expiry.
- **Masks that help and masks that hurt**: v1 zero-time memory cost 8 % (fast heroes' free actions read as refusals);
  v2 (mask on the second identical free repeat) took aborts from 11 % to 0 at equal score.
- **The derive-replay bench**: record every key, probe reply and hook truth; replay the reconstruction offline in 30 s;
  exact agreement with live. First hour: capacity wrong 6.7 % of steps ("You strain a muscle" wounds a leg; heal text
  from NetHack 3.4), pile food, a polymorph parser that never matched. Table of per-channel error before/after.
- The clock again: stock NLE runs on the real date; +1 Luck on full-moon days; AutoAscend and every other entrant
  had the same exposure.

### G. Bugs found — one table (NetHack / NLE / fork / trainer / ours)
| where | bug | effect | how found |
|---|---|---|---|
| NLE | object glyphs expose true identity (shuffled appearance not applied) | information leak | obs fairness audit |
| NLE | blstats zeroed on the terminal step | score "clawback" in the reward | death probe |
| NLE gym | reset() presses SPACE through the welcome line | identity never observable | real-env binding |
| NLE gym | challenge action set carries Enter as CR | our LF fell to ESC 550×/game | key census |
| NetHack | wall clock in gameplay (moon, ubirthday → shops/prices/labels) | non-reproducible games | rung 3/4 parity |
| NetHack | panic() → dosave0 on half-restored state | process segfault | sweep post-mortem |
| NetHack | erosion bits double as "rotten" for food | leak via item state | invariance probe |
| fork | GD-TLS + coroutines + thread migration | cross-env corruption | seed-777 repro |
| fork | getenv in RND() | 45 % of instructions | callgrind |
| fork | sysopt per-thread release | double free | 4-thread runs |
| trainer | rewards clamped to [−1, 1] | terms invisible | exact-match retrain |
| trainer | NUM_ATNS=1 with 2 heads | actions aliased across envs | determinism oracle |
| trainer | bf16 alignment vs flat fp32 master | silent checkpoint shift | float-count check |
| trainer (upstream) | advantage/CDF hoisted out of the minibatch loop | V-trace dead | 1978 vs 4077 receipt |
| ours | sticky `cant_hold` | −12 %/−19 % on stock | paired arms |
| ours | wounded legs / heal text / pile food / form parser | 6.7 %, 2.4 %, 0.25 % channel errors | replay bench |
| NetHack | `ubirthday/257` shopkeeper index overflow draws an extra `rn2` | RNG stream forks by wall clock | time sweep |
| NetHack | `#if MACOSX` gameplay branch in `eat.c` draws RNG on one platform | platform-dependent games | cross-platform goldens |
| NetHack | RNG draws in unspecified argument-evaluation order (~15 sites) | gcc -O3 vs clang dungeons differ | two-build diff |
| NetHack | `qsort` tie order in `sort_rooms` | doorway exists on one libc, not the other | golden aa_7015 |
| NetHack 3.6.6 | UAF: engulfer killed atop a level-teleport trap; shapeshifter expelled onto one | ~15 % of long runs crashed | ASan on training events |
| NetHack 3.6.6 | `dog_move` stale grid pointer after pet relocation | hours-in segfaults | seed-777 repro |
| NetHack 3.6.6 | `alter_cost` scans from the same shopkeeper forever | infinite loop | billed objects |
| NetHack | `getpos` cursor browse eats agent keys | ~1/300 caster episodes wedged 9K steps | wedge census |
| NLE | fcontext fiber stack 64 KiB overran its guard page | deep recursion crash | sanitizer |
| NLE | `nle_yield` skipped the final returncontext save | #GP on a stray key after death | repro |

## 3b. Timeline (from the two git histories; use for the narrative spine and a figure)

| date | milestone | number |
|---|---|---|
| 2026-05-25 | native C vecenv over a per-env-state NLE fork | 136K SPS at 4,096 envs |
| 2026-07-03 | restart: custom CUDA encoder + CPU/CUDA parity tests from day one | |
| 2026-07-08 | reward decomposed into NetHack's own score terms (gold, 4×exp, 50×depth) | score 1,100 |
| 2026-07-08 | fast-nle forked; golden baselines committed **before** any engine change; the one-day determinism hunt | 34 goldens |
| 2026-07-09 | thread-safety fixes + engine speedups | 69K → 172K SPS single env, 2.1–2.4× |
| 2026-07-10 | encoder split into its own file; "2800 run" | 2,800 |
| 2026-07-11 | factored actions: verb × inventory slot; underfoot glyph export | obs 3,616 B |
| 2026-07-12 | generated glyph factorization (kind, species) that cannot re-leak identities | weights 1.6 → 14.8 MB |
| 2026-07-13 | message trigram encoder | +14 % |
| 2026-07-17 | stair mask, hp ratio | 3,259 → 4,258 on one seed |
| 2026-07-21/22 | partial fills (+12 % train SPS), mmap ctx (LL write misses −39 %), terrain byte-plane | |
| 2026-07-24 | two use-after-frees fixed in stock NetHack 3.6 | one had killed ~15 % of long runs |
| 2026-07-25 | head gating merged: "5–6k score" | 5–6K |
| 2026-07-31 | champion stack: 19 heads, mask 730, verb-ε floor | |
| 2026-08-01 | fixed-trainer 1B fleet; every run beats the previous record | 8,056 ± 238 (n=3) |
| 2026-08-03 | engine exports: hero path, shop price, terrain underfoot, inside shop; two shopkeeper bugs | |
| 2026-08-10 | spells and discoveries; zero-turn cast wedges killed | |
| 2026-08-14 | NetHack Challenge protocol in the env; two shipped policies (score, depth) | |
| 2026-08-22 | first certified 1B: score config 5,807; depth config dlvl 10.78 | |
| 2026-08-25 | v5 encoder/decoder; 27 Aug "min encoder" | |
| 2026-09-03/07 | new arch + message codebook; public release (26-verb factored action space) | weights 17.2 MB |
| 2026-09-09 | 4B × 4 seeds done | mean 18,155 |
| 2026-09-11 | stock-NLE conformance ladder lands (largest commit: 219 files) | rung 4 median 8,270 (n=320) |
| 2026-09-12 | cert regression root-caused; zero-time v2 default; derive-replay bench; three derive bugs fixed | capacity 6.7 % → 0.13 % |

Score progression to plot (training interface unless noted): 1,100 (Jul 8) → 2,800 (Jul 10) → 5–6K (Jul 25) →
7,207 ± 238 @1B (Jul 30) → 8,056 @1B (Aug 1) → 12,957 @1B, 16,702 @2B, 18,155 @4B (Sep, t1122 config) →
stock/challenge medians 6.8–7.6K, AutoAscend 5,336.

**Do not use** (retracted): the overnight 2026-09-11/12 reconstruction ablation (`real0` 7,413, `derived` 5,282,
`keep_capacity` +1,046, "probes cost 35 %") ran without `NLE_GETPOS_NORMAL=1`; farlook keys landed in the game.
The corrected reference arms are `logonly` 11,377 (local) / 11,841 (second box); `derived`, `real0` and the
fixed-derive arm are finishing today. Also do not mix panel rolling finals, raw CUDA_EVAL means and burn-in certs.

## 4. Figures to produce (Sunday)
1. Score distribution, ours (rung 4, final weights) vs AutoAscend median line. From `.ep` / jsonl.
2. The ladder bar chart: mean and median at rungs 1/2/3/4 for the same weights.
3. Scaling: 1B/2B/4B fork and stock, mean and median.
4. Per-role medians (final weights, stock).
5. Death causes + food clock over game length (census).
6. Reconstruction error per channel, before/after (from the bench, already in LEDGER).
7. Training curve with the consolidation squeeze (verb rates over steps) — from an existing jsonl.
8. Engine speed table (vendored NLE vs fork; training SPS).

## 5. Schedule
- **Sat**: results in flight (canary 12:15, 2B rung 3 ~15:00, 4B lanes overnight). Write §3 A–E from the notes
  (no new data needed). Decide the title and which 4–5 arcs go in the main text.
- **Sun morning**: rung 1 certs of the six 4B lanes (6 GPUs, ~1 h); pick the best two; rung 3 both (seeds 21/32,
  ~5 h on free CPU); rung 4 Python for the best (3 h, CPU). Behaviour census on the best lane. Figures 1–6.
- **Sun evening**: fill §0–§2 with final numbers; §F with the canary outcome and the fixed-tree table.
- **Mon**: read-through against `LEDGER.md` (every number has a row), publish.

## 6. Risks
- A 4B lane crashes (two of eight did before; the drivers now capture rc) → the 2B table is the fallback claim.
- The canary shows the reconstruction fixes moved nothing → the article says the gap is probes/side effects, with
  `real0` vs log-only as the evidence; still a true story.
- Moon phase: Sunday is still new moon; fine.
