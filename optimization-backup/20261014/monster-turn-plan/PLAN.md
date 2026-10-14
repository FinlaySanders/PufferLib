# Monster-turn v2 — planning phase (opened 2026-10-14 17:15). NO ENGINE CODE until this plan is measured, written and reviewed.

Goal of the project: the fastest NetHack implementation for RL training. Engine state: ~520K instructions per policy step at IPC ~2.9
(single game per core), monster turn ≈ 65% of instructions; bit-exact micro-work landed today (+4.8% engine, +3.9% mask); further
bit-exact candidates null (B, F) or within 0.1%. Accepted standard for v2: same transition kernel (identical acceptable-move sets and
choice probabilities per decision), RNG realisation free (user, 2026-10-14).

## Why previous rewrites did not land (from the ledgers)
- Incremental dual-structure builds under bit-exactness: maintenance cost ≈ savings (compact-state 82 candidates; movement_subsystem,
  primary_movement x3, lz1/lz2 all null or slower).
- No hardware counters until 2026-10-14 (callgrind only); no decision-level validation standard other than trajectory hashes.

## Measurements (each a table here before any design)
M1 instruction/cycle census by situation: per dochug call bucketed by monster kind (ordinary hostile / wandering / peaceful / pet /
   shk-priest-guard / covetous / worm / tunneller) x distance (<=1, <=5, <=10, >10) x hero-visible, with sub-phase split (pre-move,
   mfndpos, intent/object search, post-move/display). Tool: rdtsc census build (reads only, behaviour unchanged) on the recorded
   corpus; callgrind Ir for instruction totals.                                                             STATUS: pending
M2 non-monster census: DONE (composition above)
M3 redundancy census: DONE (find_* / minliquid / newsym / mintrap per move, see above)
                                                                                                           STATUS: pending
M4 game-turn structure: DONE (5.12 turns/step, 9.1 moves/turn; tables below)
M5 hardware view at production rotation (12) on P and E cores: cycles / mispredicts / L1d / L1i per function (host perf server needed).
                                                                                                           STATUS: pending (server down)
## Design (DRAFT v0 below; M5 pending the perf server)
- Prize bound by situation, with the assumption behind each number.
- Representation (per-cell planes, SoA monster fields) sized to the dominant decisions; who maintains each plane.
- Validation harness: decision-kernel equivalence over the corpus (candidate set + choice probabilities), specified before engine code.
- Milestones with go/no-go measurements, effort, stop rule; non-goals (special monsters on the old path; display semantics untouched).

## M1 + M4 RESULTS (2026-10-14 17:32; census build = selE source + rdtsc hooks, LTO no PGO; rotation-16 harness, 128 recorded mature games,
warm 4096 / measure 16384 → 6,047,659 policy steps; rdtsc overhead ≈ 100-150 cycles per move is INCLUDED in the per-move numbers)
- Game turns per policy step: 5.12. Monster moves per step: 46.6 (9.1 per turn). Step cost 46,305 cycles.
- dochug (monster move incl. everything) = 65.9% of the step; 654 cycles per move, of which mfndpos 25% and the
  object search 17%; the remaining ~58% is dochug/m_move machinery (pre-move checks, intent, selection, position update, newsym x2, post-move).

| kind | moves/step | share of moves | share of dochug cycles | cycles/move | mfndpos | objsearch |
|---|---:|---:|---:|---:|---:|---:|
| hostile | 41.97 | 90.0% | 87.4% | 635 | 24% | 18% |
| peaceful | 3.17 | 6.8% | 8.2% | 791 | 33% | 6% |
| tunnel/passwall | 0.48 | 1.0% | 2.2% | 1,394 | 30% | 14% |
| fleeing | 0.33 | 0.7% | 1.4% | 1,267 | 22% | 12% |
| shk/priest/guard | 0.65 | 1.4% | 0.6% | 280 | 2% | 0% |
| pet | 0.02 | 0.0% | 0.2% | 3,150 | 10% | 0% |
| conf/stun | 0.00 | 0.0% | 0.0% | 3,192 | 12% | 13% |
| covetous | 0.00 | 0.0% | 0.0% | 7,428 | 0% | 0% |
| worm | 0.00 | 0.0% | 0.0% | 1,607 | 12% | 1% |

| distance to hero | moves/step | share | share of dochug cycles | cycles/move | mfndpos | objsearch |
|---|---:|---:|---:|---:|---:|---:|
| <=1 (adjacent) | 0.09 | 0.2% | 1.2% | 3,983 | 4% | 1% |
| <=5 | 1.64 | 3.5% | 6.7% | 1,239 | 18% | 16% |
| <=10 | 4.80 | 10.3% | 11.2% | 713 | 23% | 16% |
| >10 | 40.07 | 86.0% | 80.9% | 615 | 26% | 17% |

| hero can see the monster | moves/step | share | share of dochug cycles | cycles/move | mfndpos | objsearch |
|---|---:|---:|---:|---:|---:|---:|
| no | 45.81 | 98.3% | 95.8% | 637 | 25% | 17% |
| yes | 0.80 | 1.7% | 4.2% | 1,609 | 16% | 12% |

READING: 86% of monster moves (81% of monster-move cycles, ~53% of the whole step) are HOSTILE monsters more than 10 cells from the hero that the
hero cannot see; adjacent/visible monsters are 1-4% of cycles. The per-move cost is NOT dominated by mfndpos (25%) or the object search (17%): the
other ~58% is the dochug/m_move body around them. A v2 for exactly this population (ordinary hostile, far, unseen) is the design target; its
decision kernel is the simplest in the game (approach the believed hero position or wander; no combat, no items in reach most of the time).
Callgrind (8 young games, exclusive Ir) composition below.

## M2 + M3 RESULTS (callgrind, 8 young games x 768 steps = 6,144 steps, 221K Ir/step in this young regime; mature games are ~520K Ir/step)
Self cost by function (% of all instructions): m_move 19.1 | mfndpos 15.5 | obs packing (env header) 6.9 | newsym 5.9 | dochug 4.8 | movemon 3.6 |
moveloop 4.1 | vision_recalc 3.0 + left/right_side 2.2 | isaac64 2.3 | dosearch0 (hero searching) 2.2 | fill_obs 1.7 | nh_timeout 1.7 |
flush_screen 1.6 | update_blstats 1.3 | mcalcdistress 1.1 | malloc/calloc 1.1 | printf family 1.0 | find_misc/defensive/offensive 2.3 |
nh_fobj_next 0.9 | minliquid 0.9 | mintrap 0.6 | monster_nearby 0.6 | encumber_msg 0.6 | strstr 0.3 | mattacku 0.3.
Groups: monster turn ≈ 56% (young) / 66% (mature, cycles) | obs export ≈ 11% | vision/display ≈ 7.5% | per-turn bookkeeping ≈ 8.5% |
hero action ≈ 3% | allocation + formatting ≈ 2.5%.
Per monster move (young): dochug inclusive 2,674 Ir = m_move 2,201 (of which mfndpos 818, newsym x2 ≈ 245, fobj 46, mintrap 34, and the m_move
BODY ≈ 1,000 Ir: intent chain, set_apparxy, load/likes flags, flag assembly, should_displace, selection, position/track update, post-move door
and item checks) + dochug's own pre-move ≈ 470 (find_misc/defensive/offensive 130, distfleeck/disturb/m_respond/monnear, status checks).
Redundancy visible in the tree: find_misc + find_defensive + find_offensive run for every move (42 calls/step each) though the monster carries
nothing usable in >95% of moves; minliquid per move; newsym twice per move even when neither cell is visible; mintrap per move.
Tier-0 side findings (exact, cheap, not part of v2): printf-family formatting ~1%/step and malloc ~1%/step inside the step path (callers to be
identified), strstr x8 per step in the env header's cant_hold tracker (0.3%).

## PRIZE BOUND (mature regime, rdtsc census): far unseen hostile moves = 71% of monster-move cycles = ~47% of the step at ~600 cycles each.
A v2 path for that population at 200 cycles/move (3x) saves ~31% of the step → +45% SPS; at 300 cycles (2x) saves 23% → +30%; at 400 (1.5x)
saves 16% → +19%. The kernel is: believed hero position (set_apparxy), approach-or-wander intent, acceptable neighbours (mfndpos rules for an
ordinary non-tunnelling walker), nearest-cell choice with track avoidance, position update, display update only if a cell is visible.
Everything else (adjacent/visible/special monsters, pets, shopkeepers, items in reach) stays on the old path: 4% of cycles.

## ELIGIBILITY CENSUS (17:45; same run, far (>10) unseen hostile moves = 217.3M of 282M monster moves)
likes_objs 14.5% | likes_gold 38.0% | likes_gems 4.3% | likes_magic 0.4% | uses_items (non-mindless, non-animal) 51.3% | hides_under 7.2% |
flyer/floater 7.6% | swimmer/eel 5.6% | amorphous 0.9% | giant 0.0% | nohands/verysmall 80.5% | carries items 45.7% | can_track 98.5% |
undead/vampshifter 2.7% | unicorn 0.2% | human/minotaur 0.5% | bat/light/stalker (random approach) 4.8% | blinded 0.0% | asleep 13.5% |
immobile 0.0% | throws_rocks 0.0% | mercenary 0.0% | eating 0.0%.
READING: there is no small "plain walker" subset to carve out — object interest (~60%), carried items (46%) and track following (98.5%) are
the norm — so v2 must implement the full ordinary-hostile kernel (status/sleep, distance/fear, item-use early exits, believed hero position,
approach/wander/track, load and likes, object search, neighbour legality incl. liquids/doors/traps/garlic/scare rules, displacement, selection
with track avoidance, move execution, visibility-gated display, post-move trap/door/item/hide) rather than a subset; the fallbacks are the
truly special kinds (pets, shk/priest/guard, covetous, worms, tunnel/passwall, confusion/stun, adjacent or visible monsters) = ~4% of cycles.
Each listed rule is cheap in a plane/word representation; the cost today is the scattered evaluation, not the rule count.

## DESIGN DRAFT v0 (for review; no code)
Representation (per level, maintained by the existing setters; most already exist): planes nonrock, occupied (exist), pool, lava, door,
drawbridge (B), trap-present, pile bits (garlic/boulder/scare), hero-could-see (viz_array exists), hero-track bitmap (new: rebuilt per turn
from utrack), object-present (NH_SUMMARY exists); per-monster packed word: species bits (SPWQ exists), status bits, flags needed by the kernel.
Fast path: dochug_fast(m) for eligible monsters = exact re-implementation of dochug + m_move + mfndpos + post-move for the ordinary-hostile
kernel over planes/words; eligibility test is a single mask on the packed word (+ not adjacent/visible/sensed); ineligible → old code unchanged.
Validation harness (before the kernel): corpus replay with BOTH paths per eligible decision; the OLD path applies, the NEW path computes and
must reproduce the deterministic intermediates exactly: believed hero position, appr, candidate set + info flags, track-hit flags, chosen cell
(approach) or candidate set (wander), post-move state deltas. Zero mismatches over 16,777,216 decisions = gate. Then the usual quick gates,
native rot-16 A/B, trainer live run, and a paired-seed learning check (RNG realisation differs by construction).
Milestones: (1) harness + old-path intermediate dumper, with coverage report of the eligible share (go if ≥ 80% of far-unseen-hostile moves);
(2) kernel for the top properties (no items, no object interest) → mismatch-free + measured per-move cycles (go if ≤ 300); (3) items/object
interest/hide/track/liquids; (4) post-move + display gating; (5) land. Stop rule: any milestone that cannot reach zero mismatches in a week.
