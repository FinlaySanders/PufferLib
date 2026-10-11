# Encoder Representation Contract

What a NetHack encoder must be able to represent, which mechanism class can carry each demand,
how V5 covers the map, and the test suite that keeps it honest.

## 1. The core distinction: capacity vs demand

Every representational claim about the encoder is one of two different statements, and our own
results show they come apart:

- **Capacity** — *could* this architecture learn to represent X, given a task that demands it.
- **Demand** — *does* the production policy actually represent X after RL training.

Evidence they dissociate: the same encoder gives digger-role stairs decoding R²=0.995 while the
merchant probe reads 0.03; `isum` is a food-o-meter (food R²=0.85, AUC 0.995) and near-zero for
every other item class; the engineered book-known bit sat completely inert (+71, null). RL
representation is demand-driven — a probe failure on a trained net indicts the reward/task
context, not the architecture, unless a capacity test fails too.

**Consequence for the suite:** every representational property gets two test forms —
a *capacity lab* (synthetic supervision, trains the branch from scratch on a small budget)
and a *demand probe* (frozen production checkpoint, linear/MLP readout on dumps).

**The formability principle (the launcher lesson, stated as doctrine).** Demand selects among
representations the architecture can *form* — it cannot conjure unformable ones, and a missing
path fails silently: the policy converges to a plausible strategy minus a capability, with
nothing to probe (pre-wld the bow↔ammo relation was unformable, the Ranger meleed for a billion
steps, and that read as a converged strategy — not a symptom — for two eras). So the burden of
proof runs capacity-first: keep every contract class *formable* in every arm at nominal cost,
and let demand prune usage, never existence. The cost asymmetry is measured: unused capacity is
nearly free (bok bit, inert), missing capacity cost an entire playstyle. Corollary — the arm
audit gets a **formability column**: for every (feature source → entity set) pair, does a
gate→query→keys path exist? The full audit is §8; headline: wielded↔inventory proven,
item↔terrain formable, monster↔inventory/spell↔monster only softly formable (species identity
reaches h at probe 0.42 vs 0.15 floor) — one nearest-hostile GATE hardens both.

## 2. Aggregation classes — the counting vs attention problem, generalized

Most encoder branches pool a variable set (55 inventory slots, K monsters, ~1,700 map cells)
into a fixed vector. The pooling operator determines which set-level predicates survive:

| capability | max-pool | relu-sum (·ε) | softmax attention | per-slot concat | engineered |
|---|---|---|---|---|---|
| existence ∃x | **exact** | soft (count>0) | sharp query ≈ | yes | bits |
| **count** #x | ✗ | **exact-ish (linear)** | **✗ impossible** | yes | log1p hist |
| retrieval (features of the x) | winner only | ✗ (superposed) | **exact** | positional | — |
| extreme (nearest, max-danger) | **exact** | ✗ | soft | yes | nearest-k sort |
| conjunction per item (blessed∧weapon) | if φ computes it | if φ computes it | if key computes it | yes | bits |
| cross-item relation (launcher↔ammo) | ✗ | ✗ | ✗ (single hop) | tiny sets only | **match bit** |

Two theorems worth stating because they bit us:

- **Softmax attention cannot count.** Output = Σ aᵢvᵢ with Σaᵢ = 1 is invariant to duplicating
  an item: two identical daggers ≡ one dagger. Any count demand routed through IVA alone is
  unlearnable. This is why `isum` exists *beside* IVA — the dual-pool pattern is a requirement,
  not a redundancy.
- **Sums superpose.** Σφ(xᵢ) preserves any *linear functional* of the multiset (counts of
  φ-detectable classes) but destroys which features co-occurred across items. Conjunctions must
  be computed per-item *before* the sum — capacity lives in the per-slot MLP depth, not the pool.

**Where V5 stands per branch:**

| branch | mechanism | aggregation class served | evidence |
|---|---|---|---|
| `isum` 64d | relu masked-sum ×0.2 | counting | food-o-meter proven; other classes = demand-zero |
| `iva` 128d | 8 softmax queries / 55 slots | retrieval | decoder audit: composite selection works |
| `wld` 16d | wielded-bit gated sum | existence+identity of one flagged item | survives only as pool over 55 (obs-panel result) |
| `labm` 64d | 16-*nearest* tokens, per-token MLP, 8-head attn | extremes (engineered) + retrieval + per-monster binding | hazard bits engineered dims 42-45 |
| `labi` 64d | same, items | same | — |
| `terr` 128d | 12 min-cheb landmarks + 8×4×17 log1p histogram | extremes + spatial counting, **fully engineered** | knockout +70 null (demand low) |
| `spell` 36d | relu-sum ×0.2 over slot inputs | counting/existence | v3 pointer content-keyed |
| `msg` 32d | trigram-hash sum (4096×32) | bag-of-text counting | committed floor; order lost |
| `loc` 256d | 9-class LUT crop → embeds → MLP | local spatial conjunctions | — |
| `blfeat/blhid` | normalized scalars | magnitudes | [-1,1] bounded squash |
| `ide` 40d | discoveries list | identity knowledge | ABI-skew rules |

## 3. The other problem classes

Beyond counting-vs-attention, the failure archive names six more:

1. **Cross-entity relations — learnable, and the launcher proves it (source-verified
   2026-08-26).** The committed obs has NO launcher features (winrl.cc flags byte = worn/
   wielded/swap/quiver/poison/grease/erodeproof; the vendor lnc helpers are lab-census only).
   Pre-V5 (no wld readout) the relation was unformable: 0/28,764 fires — the wielded item's
   identity never reached the trunk. V5's wld gate + content-keyed pointer supplied the
   learnable path, and RL learned bow↔ammo from raw identity alone: emergent pure-archer
   Ranger, 168 fires/ep, bow wielded 93% of steps. matchlab.py confirms the mechanism at
   1.000 accuracy and shows the identity-shortcut (pair memorization, 0.997) is exactly how
   it's done for fixed rule tables. The design rule: relations need an ARCHITECTURAL path
   (gate-carried features → pointer query → entity keys; interaction stage if ever multi-hop),
   never derived-predicate obs bits — the one bits arm (NH_LAUNCH_OBS) was score-lateral and
   rightly never committed, and the bok null shows unused bits are the default outcome.
   Static rule tables (oc_skill, armor cats) remain legitimate inputs when identity
   memorization isn't enough (open-world tables, unseen combinations).
2. **Retrieval bandwidth / key capacity** — 16d inventory keys hit a content ceiling: cursed
   AUC 0.999 vs blessed 0.762. Addressable-content tests belong in the suite; key width is the
   knob.
3. **Magnitude resolution** — bounded squash saturates at extremes (gold high-water design,
   deep-HP regimes). The suite should test discriminability at operating ranges (e.g. HP 5 vs
   10 matters; 500 vs 505 doesn't).
4. **Identity vs class generalization** — E_res identity embeds (5,977) vs Kind/Sub class
   embeds; multi-role identity embeds beat one-hots (7,035@1B). Unseen/rare identities should
   degrade to class behavior, not noise.
5. **Text compositionality** — trigram bag: collisions and order loss. "You feel hungry" vs
   negated forms; the committed floor is bag-level.
6. **Temporal division of labor** — the trunk is *reactive* (NEXT-verb decode 0.324 vs 0.308
   base): the encoder must surface anything needed *this step*; the minGRU only weakly
   integrates. Anything requiring cross-step memory (search counts, shop debt narrative) either
   comes from env counters in obs or effectively doesn't exist. Suite: probe h vs probe obs for
   step-t-dependent facts; large gaps localize the responsibility.

Plus one meta-class:

7. **Affordance/legality mirroring** — the action mask encodes legality; the encoder should
   carry the *why* (CAST/EAT legality masks shipped as env features). Probe: predict mask bits
   from concat; mismatches are wasted-action pressure (hunger-refusal spam loops).

## 4. Test suite design

```
tests/nethack_repr/
  dump.c          # slim nhdump: obs, per-branch activations, concat, h — N episodes, CPU
  manifest.py     # the probe registry: (class, branch, property, label_fn, test_form, threshold)
  labels.py       # label extractors from raw obs/NLE state (counts, existence, relations...)
  probes.py       # linear + 1-hidden MLP readouts, shuffle-control, obs-ceiling control
  capacity/       # synthetic labs per mechanism (invlab-style, fixed 2-min budgets)
  run.py          # scorecard: PASS/FAIL vs thresholds + trend vs last run
```

**Tier 0 — numerics (exists):** `test_nethack_encoder.py` gradcheck + CUDA/CPU parity + the
bit-exactness A/B gate. Unchanged.

**Tier 1 — demand probes (frozen checkpoint):** dump N≈2K episodes; for each manifest entry fit
a probe on the named branch slice and on full concat. Every probe ships with two controls:
*label-shuffle floor* (kills leakage) and *raw-obs ceiling* (is the information even present in
obs — if not, it's an obs bug, not an encoder bug). Report AUC/R².
Starter manifest:
- count: food items (isum — known-good anchor), total inventory, adjacent monsters ≤k
- existence: pick-axe, unihorn, loadstone-cursed, downstairs-visible
- retrieval: wielded-item class/enchant (wld), slot-content by pointer key
- extremes: nearest-hostile distance (labm), max-monster-difficulty
- relation: launcher-ammo match (bit is in obs — encoder should carry it), Elbereth-standing
- magnitude: HP fraction at low range, gold log-magnitude, hunger state
- identity: discovery-known for k common appearances
- temporal: fact(t) from h vs from obs(t) (searched-here, recent-message decay)
- affordance: CAST/EAT legality reconstruction

**Tier 2 — capacity labs (synthetic, architecture-under-test):** generate synthetic slot/monster
multisets with controlled labels; train the branch + a head from scratch, small fixed budget;
assert learnability. These catch *architectural* regressions the demand probes can't: swap isum
for attention → count-capacity fails loudly; shrink keys 16→8 → retrieval-bandwidth fails.
One lab per row of the §2 table diagonal (existence/max, count/sum, retrieval/attention,
conjunction/per-slot-depth, relation/expected-fail-without-bit).

**Tier 3 — in-vivo behavior (env stats):** kit-audit counters as integration assertions on any
new 250M run: launcher-fire rate > 0, wear rate, zero-cast regression, waste-loop census.
Cheap, already logged.

**Pass semantics:** Tier 0/2 are hard CI gates (deterministic). Tier 1 is a *scorecard with
trend* — absolute thresholds only for anchors we've certified (food counting, cursed retrieval);
everything else reports drift vs the last accepted checkpoint, because demand legitimately moves
with reward changes.

## 5. Known-answer anchors (calibration set)

Facts any correct run of the suite must reproduce, from prior campaigns: isum food R²≈0.85 /
AUC≈0.995 and ≈0 elsewhere; cursed-key AUC≈0.999, blessed≈0.76 at 16d; wld wielded-identity
survives pooling; digger stairs R²≈0.99 vs merchant ≈0; bok-bit ≈ null; launcher-match carried
only via the engineered bit. If a fresh suite disagrees with these on the era checkpoints, the
suite is wrong.

## 6. The canonical set arm — FINAL FORM (2026-08-26)

**Two layers, cleanly separated (user decision):**

**(a) The generic pooling unit** — uniform across all entity arms, no per-domain configuration:
```
r_s = relu(W [id_embed | feats]) ⊙ occ ;  v_s = relu(V r_s)
out = [ attention (LN, 1/sqrt d, cold) | sigmoid-count | plain sum ×ε | max ]  over v
KEYS = r_s  iff pointer-addressable
```
No seeds, no temperatures, no named channels. Evidence: sweeps the full synthetic battery at
1.00 (first design to do so — patchwork prodtrip: 0.76 extremes); ties the hand-designed arm
on real data (family means 0.855 vs 0.853, protocol-matched); cold RL cert 3,860 ≈ champion
3,618 at 250M; K-lottery test shows K=8 suffices (no gains to K=64). Known residuals: shared-V
conjunction interference (~-0.08 vs dedicated isum; per-channel V is the knob), real-regime
max_ench ceiling ~0.75 is distribution shift shared by all designs.

**(b) Structural featurization** — per-modality, explicit, each row audited with a
justification: env-pointer PASS-THROUGHS (wielded [r|sfeat] — proven by the archer; quivered —
proposed, fire-action pair; worn-profile r — cheap insurance; nearest-hostile = monster
token-0; underfoot = item token-0), coordinate framing (hero-centering), orderings
(distance sort), EXACT scalars/tables. Pass-throughs are attention with env-given weights
(dict lookups on game-state pointers, e.g. uwep) — input plumbing, NOT pooling. Budget: the
3-row inventory instantiation ≈ 96 dims vs today's 16; the full ~20-row closure stays a
documented option, one config line per row.

The learnability boundary, measured: gradient descent handles content (what to represent) and
soft selection; it cannot at our budgets discover hard selection — by env-pointer (plateau:
0.3-0.6 cold vs 0.84-0.92 given) or needs the max primitive for order statistics (1.00 with,
0.6-0.8 soft without on clean data). Structure supplies pointers and order; learning supplies
content.

**The attention question, settled (adversarially reviewed 2026-08-26):**

> fixed questions → statistics · answered questions → lookups · live questions → decoder
> attention · candidate-vs-reference relations → the query · set-relative selection → the
> softmax itself (set margins/counts → statistics) · candidate-vs-candidate relations →
> hand-built fields or one self-attention round — NetHack's env hand-builds them, and the
> residue is audited-empty.

Supporting mechanics: (a) pooling attention has frozen queries → degenerates to a statistic →
statistics primitives do it directly (deletion cost ≈ 0, measured); (b) the pointer decoder's
softmax IS the cross-candidate competition, so argmax-type set-relative selections need no
encoder cross-talk; (c) reference relations factor through the query — bilinear scoring
computes (features of reference)·(features of candidate), e.g. q=(1,−dmg_wld,…)·k=(dmg_s,1,…)
= dmg_s − dmg_wld — provided the relation is expressible in that bilinear form (the query MLP
covers mild nonlinearity; gnarlier reference relations are the honest boundary); (d) cardinal
set information (margins, gaps, densities) is NOT carried by selection — it rides the
statistics channels into h, where other logits and the value head consume it; (e) the tier-3
(candidate×candidate) emptiness claim must be checked against COMPOSED predicates
(set-relative × pairwise), quantified over the actual action space — currently satisfied
because no verb conditions on any such composition.

(Original §6 below for history.)

## 6-old. The canonical set arm (superseded)

Every entity-set branch (inventory, spells, monsters, floor items) is one pattern; the
[set-encoder race](https://claude.ai/code/artifact/02298a91-86ff-40ae-9265-b88eaae948fe)
fixes which readouts exist and why:

```
inputs   x_s = [identity embeds | state features]        masked by occupancy
shared   r_s = relu(W x_s)          width 16 suffices (race: width a non-factor)
expand   h_s = relu(V r_s)          the per-entity conjunction stage (depth before pooling)

readouts — one per demanded contract class:
  KEYS = r_s                        decoder pointers ONLY (never starves the trunk — verified)
  SUM  = Σ h_s × ε                  counting        (duplication-exact; quan stays linear)
  MAX  = max h_s                    extremes        (duplication-invariant)
  ATTN = M-query softmax over r     retrieval       (cannot count — 40% duplicate undercount)
  GATE = Σ flag_s · r_s             flagged-entity identity (wielded, worn, …)
  EXACT = engineered scalars/bits   extremes or relations too important to leave to learning
```

Two structural rules: **relations are not poolable but they are learnable** — route them
through gate-carried features + content-keyed pointers (proven: the bitless V5 archer) or an
interaction stage if ever multi-hop; derived-predicate bits are not part of the pattern. EXACT
is reserved for *static rule tables* and closed-form facts (doorstep scalars, landmarks) —
basic game information, never decisions.

**Instantiation audit:**

| arm | KEYS | SUM | MAX | ATTN | GATE | EXACT | verdict |
|---|---|---|---|---|---|---|---|
| inventory (55) | ✓ 16d | ✓ isum | **✗ — the gap** | ✓ IVA-8 | ✓ wld | launcher-bit | add MAX (0 params, reuse isum hidden) |
| spells (5) | ✓ 16d | ✓ sp2 (raw-read variant) | via EXACT | — (CAST pointer suffices) | — | ✓ min_fail/max_lev/n/retention | **already pattern-complete** |
| monsters (labm, 16-nearest) | — | **✗** | via EXACT (nearest-k sort, hazard bits) | ✓ 8-head | — | dist-sorted k | counting gap predicted — attn-only can't count a swarm |
| floor items (labi) | — | **✗** | via EXACT | ✓ | — | ✓ | same counting gap |

Spells need no change: with 5 slots, the doorstep scalars *are* the MAX/MIN channel, computed
exactly — the engineered-substitute rule in action.

**The unified arm is now validated on token streams too (tokenlab.py, 2026-08-26)**: on real
monster-token data the production labm (attention-only) counts at R² 0.71-0.72 while the
unified arm (sum ‖ max ‖ attn8 ‖ token-0 gate off one shared 16d rep) hits 0.96-0.98, matches
or beats it on every retrieval/extreme column, and the token-0 gate doubles as the audit's
nearest-hostile formability fix (for the item stream, token 0 at distance 0 IS the underfoot
gate). **The optimal entity encoder, both modalities:**

```
EntityArm: r_s = relu(W [id_embed | feats]) ⊙ occ        (W=16 suffices)
  SUM  = Σ relu(V r_s) × ε          counting
  MAX  = max of the same relu(V r_s) extremes (shared V — free)
  ATTN = 8-query softmax over r      retrieval
  GATE = focused-entity r            flag-gated (wielded) or token-0 (sorted streams)
  KEYS = r                           iff pointer-addressable
  EXACT scalars                      where closed-form
```

Production deltas implied (all cheap; concat grows ~288, proj +~150K params): inventory +MAX;
labm +SUM +MAX +gate0; labi +SUM +MAX +gate0(=underfoot). Spells unchanged. Each delta is
capacity-validated here; RL value stays subject to the paired-run rule.

All capacity claims here are race-calibrated; demand still decides what converts to score,
and every production change keeps its paired-RL-test requirement.

## 7. The universal arm

The canonical set arm of §6 is not inventory-specific. Every V5 branch is the same three-step
schema — **entities → per-entity featurization → class-appropriate pools** — where the modality
only decides what an entity is, which readouts are demanded, and whether a channel is learned
or engineered:

| branch | entity | featurization | readouts in use |
|---|---|---|---|
| inventory | slot (55) | embeds + state feats → 16d | KEYS + SUM + ATTN + GATE (+MAX pending) |
| spells | slot (5) | embed + 4 scalars → 16d | KEYS + SUM + EXACT(min/max scalars) |
| monsters/items | nearest-16 token | token MLP | ATTN + EXACT(dist-sort, hazard bits) |
| terrain | map cell (~1,700) | class LUT | **all EXACT**: SUM = sector log1p histogram, MAX/MIN = landmarks |
| message | trigram | hash-embed | SUM (normalized bag) |
| blstats | scalar fact | normalize | CONCAT (small fixed set) |
| local crop | crop cell | class embed | CONCAT-with-geometry (small, positionally structured) |
| trunk | timestep | concat proj | order-aware pool (minGRU) — the temporal instance |

The terrain branch is the purest illustration: it is the inventory arm with every channel
engineered — cells are entities, the sector histogram is its SUM, the landmarks are its MAX/MIN
— which is why it needed no learning to be complete.

**Channel-selection rules** (the whole design procedure):
1. Name the entity and its per-entity features.
2. List the contract classes the arm must serve (§2/§3).
3. Pick readouts from the menu — one per class. Prefer **EXACT** when the fact is closed-form
   and small (spell doorsteps, landmarks); **CONCAT** when the set is small and fixed
   (blstats, crop); learned SUM/MAX/ATTN/GATE otherwise.
4. **KEYS** iff actions point at the entities (inventory, spells — not terrain, not messages).
5. Relations: learnable-first (content-keyed pointers, interaction stage if demanded);
   derived-predicate bits last resort. Static rule tables are legitimate inputs. Conjunctions
   need depth *before* the pool. Sums get ε-scaling and occupancy masks; features in [-1,1].

**Where the schema bends**: the local crop keeps geometry (a set view would discard adjacency —
CONCAT-with-structure is the right reading, not a violation); the trunk pools an *ordered*
sequence, so its aggregator is a recurrence rather than a symmetric pool; and global spatial
reasoning (pathing) is deliberately left to EXACT terrain features rather than learned pooling.
Those are the modality's structure showing through the pattern — the pattern tells you which
channel menu applies, the structure tells you which member to pick.

## 8. Formability audit (2026-08-26, source-verified + demand-probed)

Every relation a NetHack policy could plausibly need, against the paths that exist in the
committed V5 tree. Demand probes ran on the champion's h (240K frames, declab dumps): focused-
monster SPECIES decodes at top-1 0.418 vs 0.153 shuffle floor (weak), distance R² 0.36,
underfoot-item presence 0.836.

| # | relation | path today | verdict |
|---|---|---|---|
| 1 | hero ↔ monsters | EXACT per-token (dx/dy, hazard, diff, speed) + threat block | ✓ served |
| 2 | hero ↔ floor items | EXACT per-token (dx/dy, oclass, identity row) | ✓ served |
| 3 | hero ↔ terrain | EXACT (landmarks, sector histogram, crop) | ✓ served |
| 4 | wielded ↔ inventory | GATE(wld) → query → inv keys | ✓ **proven** (archer) |
| 5 | wielded/worn ↔ monster | wld ‖ monster summary → trunk conjunction; dir heads read crop | ◐ class-level ✓; species-level weak (h probe 0.42) |
| 6 | monster ↔ inventory (species-specific item choice; corpse identity is species-glyph, so carried-corpse decisions are inv-key formable) | labm attn (soft) → h → pointer query | ◐ formable in principle, not sharp in practice |
| 7 | spell ↔ monster | CAST pointer conditioned on h | ◐ same species limit |
| 8 | item ↔ terrain (pick-axe↔diggable, tool use) | per-oclass inv counts (engineered) ‖ crop → trunk; APPLY pointer selects | ✓ formable |
| 9 | inventory ↔ inventory (dip/put-in: two-slot verbs) | none — decoder has one slot pointer per verb | ✗ **justified**: action space has no two-slot verbs; becomes real only if added |
| 10 | monster ↔ monster (pairwise) | pooled summaries only | ✗ **justified**: no current decision needs it |
| 11 | message ↔ state | msg bag ‖ everything → trunk | ✓ class-level |

**The two live holes are ◐ 5–7, and they share one fix: a nearest-hostile GATE** — concat the
per-token features of monster token 0 (already distance-sorted) directly, bypassing the
attention pool: ~48 dims, zero parameters, makes species-level monster↔inventory/spell queries
formable and sharp. Second, cheaper still: an **underfoot GATE** (labi token at dx=dy=0) —
pickup/floor-eat decisions (live demand: the corpse/lichen equilibrium) currently ride a 0.836
soft signal. Both are formability insurance priced at ~nothing; demand prunes usage. Per-verb
two-slot pointers (#9) stay justified-✗ until the action ladder adds such a verb.

## 9. Tier-3 audit (2026-08-26): candidate×candidate relations over the actual action space

Action space (source-verified, netlib.h): 26 verbs; arguments = ≤1 slot pointer + ≤1 direction
(8-way) + CAST's spell slot. **No entity-pointer targeting (monsters are addressed by
direction), no two-slot verbs.** Reductions available: focus/lookup · reference-in-query ·
softmax-competition (set-relative selection) · type-factoring (per-type statistics) ·
cardinal statistics (margins/counts → h) · **the 9×9 crop** (per-cell concat = ALL k-way
spatial relations within the window are formable — §2's "per-slot concat" column) ·
env-EXACT masks.

| decision | pairwise content | reduction |
|---|---|---|
| MOVE/RUN direction | joint local geometry (monsters, walls, escape routes) | crop (joint-complete ≤9×9); beyond: sector statistics |
| KICK direction | adjacent target | crop |
| THROW/ZAP direction | ray hits/avoids entities | per-token collinearity features + **env hostile-ray mask (EXACT, nethack.h:421)** |
| THROW slot | ammo ↔ wielded launcher | reference-in-query (tier 1, proven live) |
| WEAR/PUTON/TAKEOFF/REMOVE slot | candidate vs worn; best-of-set | worn lookup (reference) + softmax competition; engine mask enforces slot conflicts |
| WIELD slot | best weapon vs current | max statistic + competition + reference |
| DROP slot | worst item | competition (negated scores) |
| EAT/QUAFF/READ/APPLY/ZAP slot | per-item content vs situation | content in keys, situation in q(h) |
| CAST spell | spell vs situation | keys + q(h) |
| no-arg verbs (PRAY, SEARCH, ELBERETH, PICKUP, TIP, ALTAR_ID, ENGRAVE_ID, UP/DOWN) | none | h statistics + underfoot focus |
| value function | threat structure, margins, densities | cardinal statistics + crop |

**Composed predicates** (the review's requirement): every composition with a pairwise factor
routes through the crop (local, joint-complete) or statistics (global) — e.g. "flee nearest
while avoiding second" = dir from crop; "throw at nearest without hitting X" = env ray mask.
No composition over this action space requires an unreduced candidate×candidate term.

**Verdict: tier 3 is empty — now by enumeration, not assertion.** Documented residuals:
(a) joint geometry of multiple monsters BEYOND the 9×9 window is approximated by sector
statistics (justified: distant joint geometry has negligible one-step decision value and the
crop refreshes every step); (b) reopeners: entity-pointer targeting or any two-slot verb —
either reopens this audit, and the contingency (one 55×55 self-attention round) stays priced.
