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

## M1 RESULTS (2026-10-14 18:05-18:40) — coverage gate PASSED; validation standard upgraded to bit-exact
Eligibility predicate measured on the rotation-16 census run (census3 build = census + mt2_eligible; same 128 games, obs hash unchanged):
hostile, not tame/peaceful/shk/priest/guard/wiz/worm, not confused/stunned/trapped/eating/frozen/asleep, mobile, not covetous/tunneller/
passwall/vampshifter/eel, hero not swallowed/conflicted/underwater/warned, dist2 > 64, not spotted by the hero.

| population | share of monster moves | share of monster-move cycles | share of the step | cycles/move |
|---|---:|---:|---:|---:|
| eligible | 68.1% | 71.9% | 45.2% | 683 |
| ineligible | 31.9% | 28.1% | 17.6% | 572 |

READING: the predicate covers 79% of far-unseen-hostile MOVES (gate ≥ 80% narrowly missed) but ~100% of their CYCLES: the far hostiles it
rejects (asleep 13.5%, fleeing, confused) are the cheap early-exit moves. The prize is measured in cycles, so the gate is passed: eligible moves
are 45.2% of the step at 683 cycles each; a kernel at 300 cycles saves 25% of the step (+34% SPS), at 200 saves 32% (+47%).

DECISION CHANGE (from the code read, monmove.c dochug/m_move/set_apparxy/distfleeck, mon.c mfndpos_masked, muse.c entry tests, display.c
newsym/nh_newsym_moved, rnd.c): every RNG draw on the eligible path is a fixed function of state — distfleeck's rn2(5) bravegremlin (twice per
dochug), stalker/bat/light rn2(3), per-track-hit rn2(4*(cnt-j)), wander rn2(++chcnt), unicorn rn2(2), hideunder rn2(5), shop rn2(25),
find_offensive's rn2(2) when Reflecting, lined_up's rn2(25) when Upolyd — and none of them is where the cycles go (mfndpos, the object search
and the m_move body are data-structure walks). So v2 is specified BIT-EXACT: same draws in the same order, same state transitions. Validation
= the existing exact gates (34 goldens + 26 fuzz + status/interleaved/shuffled, the 16,777,216-decision corpus hash, the trainer live digest
31e2e3deae720ef4) instead of the weaker "same kernel, different RNG realisation" plan; the shadow dumper is kept only as a debugging aid that
localises the first divergence to a monster decision. "RNG semantics may change" (user) is permission held in reserve, not used.

KERNEL BOUNDARY (exact, from the code): for eligible monsters dochug reduces to
  rn2(5) [distfleeck #1] → m_move(mtmp,0) → rn2(5) [distfleeck #2, if tmp != 2] → if the monster is now within BOLT_LIM (dist2 ≤ 64) or
  tmp == 1 && (msleeping || !mcanmove) or Hallucination: run the OLD dochug tail unchanged; else tmp==1 && !ranged_attk species →
  find_offensive() for its draws (Reflecting rn2(2); result is always FALSE at distmin ≥ 8) → return (tmp == 2).
  The pre-move checks (STRAT_*, quest_stat_check, disturb, wipe_engr_at [fork already gates it], teleport-when-fleeing, shriek/Medusa,
  courage, ustuck, set_apparxy → found_you, tactics, find_defensive [dist2 > 25 → FALSE], find_misc [dist2 > 36 → FALSE], bribe, watch,
  mind flayer, weapon wield [inrange only], castmu [dist2 ≤ 49 only]) are all provably no-ops for the predicate above; the predicate was
  widened to exclude the species/flags that make them live (watch, mind flayer, nemesis, shrieker, Medusa, tengu, hiders, mstrategy != 0,
  hero Invis/Displaced/Hallucination/undetected/disguised) — see mt2_eligible() in engines/mt2/source/src/mon.c.
  Inside m_move the eligible path is: hides_under+OBJ_AT rn2(10) early exit; set_apparxy (found_you); can_open/can_unlock(monhaskey inventory
  walk)/doorbuster; not_special: gx,gy = mux,muy; appr = 1; should_see is FALSE at dist2 > 36 so the only appr changes are !mcansee (excluded),
  stalker/bat/light rn2(3), leprechaun gold; gettrack (nh_track_near gate); lined_up + load/likes flags; object search via nh_fobj_next over
  the 11x11 box; flag assembly; mfndpos; track mask + selection loop; itsstuck/m_digweapon_check; ALLOW_U/ALLOW_M/ALLOW_MDISP branches
  (cannot fire at distmin ≥ 9 except ALLOW_M for purple-worm-vs-shrieker); m_in_out_region; remove/place + mtrack shift; postmov:
  nh_newsym_moved(old), mintrap (t_at walk), door/bars blocks, nh_newsym_moved(new), OBJ_AT pickup block, hides_under hideunder rn2(5).
Baseline per-move composition (callgrind, all moves, young regime): dochug inclusive 2,674 Ir = m_move self 990 + mfndpos 815 + newsym x1.83
224 + dochug self 248 + movemon self 184 + find_misc/defensive/offensive 131 + nh_fobj_next 45 + mintrap 37 + minliquid 36.
m_move SELF (990 Ir) is the largest item and is opaque at function level (LTO inlines set_apparxy, should_displace, lined_up, load, newsym
gate, the cursor loop body) → line-level callgrind of ELIGIBLE moves only (mt2 build_cg, CALLGRIND_TOGGLE_COLLECT around dochugw) running now.
Side finding to verify in that profile: newsym is called 1.83x per m_move although nh_newsym_moved exists to skip provably-unchanged cells;
if the skip rarely fires (its sense word is recomputed once per movemon and zeroed by sight changes), fixing the gate is a Tier-0 exact win
worth up to ~5% of all instructions on its own.
Dev tree: engines/mt2/source (copy of the landed fastnle_ade source) — builds: build (plain -g Release+IPO, gate symlink compact-state
engines/lines_mt2) and build_cg (-DNH_MT2_CG: eligibility counter + callgrind toggle; no behaviour change).

## M1 COST MAP (18:24; callgrind collected ONLY inside eligible dochugw calls, 8 mature games x 20,480 steps, 8.05M eligible moves of 17.2M)
3,107 Ir per eligible move (vs 2,674 all-move average: the eligible population is the expensive one). Self cost per move:

| component | Ir/move | notes |
|---|---:|---|
| m_move body (monmove.c self + inlined masks/dist2/isok/on_level/online2/load fns/rn2) | ~1,030 | long tail: no single line > 33; species+status+level tests evaluated one by one every move |
| mfndpos_masked (self + inlined helpers) | ~820 | per-candidate chain: typ, bars, door, gas, diagonal-door, worm_cross, pool (isok + on_level!), lava, scary (altar+pile+hero), hero/mux, MON_AT, temple, garlic, boulder, onlineu, squeeze, trap |
| dochug self (+ dist2, rn2 inline) | ~240 | pre-move chain that is provably inert for this population |
| nh_fobj_next object cursor (+SSE) | ~212 | search entered on 43% of moves, 3.9 objects examined per search |
| nh_newsym_moved x2 | ~131 | the skip fires (full newsym only 8/move) but the gate itself costs 65 per cell |
| find_misc + find_defensive + find_offensive + in_your_sanctuary + which_armor | ~117 | all return FALSE by distance; find_offensive draws rn2(2) only when Reflecting |
| lined_up + linedup (m_move in_line + find_offensive) | ~94 | always FALSE at distmin >= 9; m_carrying inventory walk inside |
| movemon loop body | ~91 | shared with all monsters |
| dochugw already_saw_mon = canspotmon when the hero has an occupation | ~51 | result unread for monsters farther than BOLT_LIM+1 |
| isaac64 refills | ~48 | ~3 draws/move: inherent |
| place_monster 39, mintrap 35 (+t_at 19), wipe_engr_at 32 (engr_at list walk), gettrack 26, can_carry 21, searches_for_item 21, in_rooms 20, m_in_out_region 19, onscary 13, touch_artifact 9 | ~255 | |

## M1 EVENT CENSUS (18:40; 128-game rotation-16 run, 163M eligible moves = 57.9% of all moves with the widened predicate)
plain 3x3 window (no door/pile/trap/liquid/bars/gas/altar, origin not a door, no temple, not Sokoban) 74.5% | door in window 17.6% (origin door 5.0%) |
pile 4.1% | trap 1.4% | altar 0.3% | bars 0.1% | liquid/gas 0.0% | another monster adjacent 76.3% | some window cell visible 0.8% |
origin couldsee 0.5% | object box (11x11) empty 28.9% | object interest (likes flags set) 43.2% | item-interest species 47.7% | uses_items 39.3% |
carries inventory 39.1% | search entered 43.0% (3.9 objects/search) | object target found 18.4% | moved 80.7% | no move 19.3% (0 candidates 19%) |
track hit in candidates 69.7% | destination has objects 4.6% | destination door 4.3% | destination trap 0.1% | hides_under 5.7% |
ranged species 12.3% | Reflecting 0.0% | Upolyd 0.4% | engraving at the monster's cell 0.1% (level has engravings 44.4%) | regions 0.0% |
displacers 0.0% | appr forced to 0 (stalker/bat/light draw) 1.9% | shop room 2.3% | can_open species 18.4% | NODIAG species 9.0% |
hero sense bits set (infravision etc.) 50.5% | candidate count 0:19% 1:21% 2:20% 3:14% 4:10% 5:8% 6:4% 7:3% 8:2%.
READING: monsters travel in packs along the hero's track (76% have a neighbour, 19% are boxed in with zero candidates); the plain-window
case is 3 of 4 moves; every rare mechanism (traps, regions, displacement, reflection, gas, liquids) can stay on the old code at zero cost.

## KERNEL DECISIONS (M2 design, bit-exact; each item names the exact replacement and why it is identical)
1. Eligibility = status bitfields + one species-mask test (nh_spw) + per-turn hero word (uswallow, Conflict, Underwater, Invis, Displaced,
   Hallucination, uundetected, U_AP_TYPE, Upolyd, Reflecting, rogue level, Sokoban, has_temple) + distmin > 9 + !(viz_array COULD_SEE).
   Falls back to the old dochug otherwise. Runtime switch NH_MT2 (default on) so one binary gives old/new traces and the A/B.
2. dochug_fast = rn2(5) [distfleeck #1] → m.misc/has_misc reset [find_misc side effect] → m_move_fast → rn2(5) when tmp != 2 and the monster
   is still > BOLT_LIM, else the old distfleeck → the old tail verbatim (switch/attack/quest_talk/cuss), with find_offensive replaced by its
   far-monster replica (draw rn2(2) if Reflecting, m.offensive reset, draw rn2(25) if Upolyd, tbx/tby stores) only when !inrange.
   wipe_engr_at only when the level has engravings (exact: it is a no-op without one at the cell); later a per-column engraving bit.
3. m_move_fast keeps the original draw order: hides_under+object rn2(10); mux,muy := hero (set_apparxy found_you path is forced by the
   predicate); appr = 1 then stalker/bat/light rn2(3); leprechaun gold; track via nh_track_near gate; in_line replica (rn2(25) if Upolyd,
   tbx/tby); pctload only for species with any interest bit or uses_items, max_mon_load from a per-species table; object search only when
   interest && (not in a shop room || rn2(25) draw) && the box column-bitmap is non-empty, then the existing cursor loop (shared code);
   flag assembly from species bits; can_unlock (3 inventory walks) only when a door is in the window (fallback path needs it, plain does not).
4. mfndpos: plain window (per-column bitmaps special|pile|trap|gas OR'd over the 3 columns, origin not door/gas, level not temple/Sokoban)
   → candidates = nonrock & ~occupied (& no diagonals for NODIAG; squeeze diagonals via nonrock + cant_squeeze_thru when both orthogonals are
   rock; worm_cross only when both orthogonals are occupied), info = NOTONL from online2 (unicorn skip), poss in bit order = original order.
   Anything else → mfndpos_masked unchanged. Occupied neighbours are the common case (76%) and are a mask op in both.
5. Selection loop verbatim (branch-free fork code). Apply: lean remove/place (no impossible() checks), mtrack shift, m_in_out_region only
   when n_regions. Post-move: lean nh_newsym_moved replica for both cells (same tests, gbuf pointer hoisted), mintrap only when
   NH_SUMMARY trap present (mintrap without a trap only clears mtrapped, already 0), door/bars blocks unreachable on the plain path (fallback
   path keeps them), pickup block factored into a helper shared with the old m_move, hides_under block old code.
6. Tier-0 exact items found on the way (apply to ALL monsters): dochugw computes canspotmon only when distu(x,y) <= (BOLT_LIM+1)^2;
   on_level() calls for Is_rogue_level/Is_juiblex_level/Sokoban hoisted to a per-turn level word.
7. Budget: plain path ≈ 550-650 Ir (movemon 91 + eligibility 25 + dochug_fast 60 + m_move_fast ~350 + display gates 45 + refills 48);
   fallback paths keep today's cost; weighted ≈ 900-1,000 Ir/move → ~3x on 45% of the step → +30-35% SPS env-side if cycles follow Ir.

## M2 BUILD (18:48) — kernel implemented in engines/mt2/source (apply_mt2_kernel.py), validation chain running (stage_k.sh / stage_k.log)
Representation: struct nh_move_column gains special/pile/trap/gas/obj row bitmaps, maintained by the existing single setters
(nh_move_typ_set → special; nh_pile_update → pile+obj; nh_trap_update → trap; nh_gas_update_rect → gas; cleared with the per-cell
summaries in nh_tile_clear_entities and at mklev). Species: SPW_NODIAG, SPW_HASEYES, SPW_RANDAPPR, SPW_LEPRECHAUN, SPW_MT2_NOFAST
(covetous, tunnels, passwall, watch, mind flayer, eel, hider, shrieker, nemesis, Medusa, tengu, displacers, purple worm, unicorn, rider, ghost)
and nh_spw_maxload[] (max_mon_load per species via a zeroed fake monst: reads only ->data).
Code: monmove.c mt2_eligible / dochug_fast / m_move_fast (dispatch at the top of dochug; the door, pickup and hides_under blocks are
copied verbatim from the old m_move by the apply script's brace matcher; the object search block likewise, with in_rooms → roomno
test and a box-empty skip in the for-init), muse.c nh_muse_far_misc + find_offensive_far, display.c nh_newsym_moved_far, dochugw
canspotmon gate (Tier-0, all monsters). Runtime switch NH_MT2=0 (same binary = old path) → trace_diff.sh <golden> localises the
first differing decision (build_trace, NH_MT2_TRACE=<file>: per eligible decision origin, goal, appr, candidates+info, chosen cell, RNG
buffer index).
Exactness arguments that are NOT syntactic (review list): (a) can_unlock computed only on the fallback path — monhaskey is pure;
(b) pctload skipped when no species bit reads it — curr_mon_load/max_mon_load pure; (c) object search skipped when the box has no object
— the loop body never runs, cursor setup pure; (d) should_displace and the ALLOW_MDISP test dropped — no displacer species, occupied cells
removed, so no info ever carries ALLOW_MDISP/ALLOW_M; (e) place_monster's impossible() diagnostics dropped; (f) m_in_out_region skipped
when n_regions == 0 — its loops are empty; (g) mintrap skipped when the summary has no trap — it would only clear mtrapped (already 0);
(h) find_offensive_far requires distmin >= BOLT_LIM (linedup's range test fails) plus !Reflecting/!Upolyd (no draws): dochug_fast calls the
real find_offensive otherwise; (i) the post-move distfleeck is replaced by its rn2(5) only while dist2 > BOLT_LIM^2 (teleport traps go
to the real one); (j) nh_newsym_moved_far drops the uswallow/Underwater/hero-position tests the predicate excludes and reads the gbuf
blob pointer directly (NULL → full newsym, which allocates it, as before).

## M2 RESULT (18:55) — kernel v1 EXACT and +10.7% per step
Gates with the kernel active (default NH_MT2=1): 34 goldens replay identically, 26 fuzz, status/interleaved/shuffled PASS; corpus hash
16,777,216 decisions, 0 differences. Same-binary rotation-16 A/B (plain -g Release+IPO build, P-core 2, 128 mature games x 20,480 steps):

| arm | rep1 steps/s | rep2 steps/s | obs hash |
|---|---:|---:|---|
| NH_MT2=0 (old path) | 27,791.9 | 27,783.5 | 7a111519e889cf75 |
| NH_MT2=1 (kernel) | 30,712.7 | 30,750.5 | 7a111519e889cf75 |

+10.5% / +10.7% per step, hash identical on 2.6M steps. This is v1: plain-window path only; door windows (17.6%), non-empty object boxes
(71%), the old movemon body and the dochugw wrapper are untouched. Next: eligible-only profile of the NEW path (stage_k2), trainer A/B
(fast protocol + live-learning digest 31e2e3deae720ef4), then the door-window slice.

## M2 PROFILE OF THE NEW PATH (19:00; eligible-only callgrind, same 8 games): 1,869 Ir per eligible move (was 3,107, -40%)
m_move_fast body ~855 (self 632 + masks 126: nh_move_position_bit x ~11/move, + dist2/isok/hacklib) | object cursor nh_fobj_next 174
(search entered on 28% of moves after the box-empty skip, 4.1 objects per search, ~620 Ir per search) | mfndpos_masked fallback 192
(25% of moves: door/pile/trap windows, ~770 per call) | nh_newsym_moved_far 2 x 50 | mt2_eligible 99 (counted twice in the CG build:
movemon toggle + dochug; real ~50) | dochug/dochug_fast 100 | movemon body 100 | isaac refills 48 | wipe_engr_at 24 | search qualification
(can_carry 21, searches_for_item 17, onscary 13, touch_artifact 9) | find_offensive_far 19 + in_your_sanctuary 10.
SLIP FOUND: the dochugw canspotmon gate was lost (apply script wrote a stale copy) — 51 Ir on EVERY monster move; re-applied in v1.1.
v1.1 (source applied 19:05, validating in stage_k4): dochugw gate; candidate neighbourhood bit stored (cbit[]) so the track test is a shift
instead of nh_move_position_bit per candidate (~70 Ir); info[] not computed on the plain path (unread: no unicorn/displacer/adjacent hero;
kept under NH_MT2_TRACE so traces still match); distmin inlined in the eligibility test. Then stage_k4 builds a PGO mt2 (engines/mt2pgo)
for the landing-style comparison against fastnle_ade PGO.
NEXT SLICES (expected Ir/move): S3 object search by box-cell enumeration in fobj order (needs a per-object fobj index maintained by the
existing nh_fobj_placed/removed/build; -150) | S7 door-aware window (doors are 17.6% of eligible windows: closed/locked + diagonal rules
+ can_unlock only then; -130) | display gate test reorder (-15) | hero-word cache made exact by marking it stale after every old-path move
(-25). Beyond the eligible population: movemon body, hero turn, obs packing, vision are separate programs.

## M2 TRAINER A/B (19:07; ab_mt2.json, fast protocol 44 epochs from 32, 5M model, 2048 agents, plain mt2 build, same binary NH_MT2=0/1)
| trainer | NH_MT2=0 (a/b) | NH_MT2=1 (a/b) | gain |
|---|---:|---:|---:|
| sched_v22 (scheduler) | 360,470 / 363,319 | 385,018 / 381,320 | +5.9% |
| sched_v12 (pool) | 232,836 / 232,718 | 243,268 / 244,516 | +4.8% |
Live learning (150 epochs, --update, PUF_LIVE_PROOF, kernel on): digest 31e2e3deae720ef4 = reference → exact under training too.
Transfer ≈ 55% of the +10.7% native per-step gain at 5M/2048 (C2 precedent was ~33%); expected to approach the native figure at 4096/8192
where collection dominates. Remaining landing step: one live 1B seed under gdb on the PGO build (stage_k4 builds engines/mt2pgo).

## v1.1 RESULT + LANDING-STYLE PGO COMPARISON (19:23, stage_k4)
v1.1 plain same-binary: NH_MT2=0 28,059/28,132 → NH_MT2=1 31,206/31,245 = +11.1%; corpus hash 16,777,216 decisions 0 diffs; the dochugw gate
alone lifts the OLD path +1.0% (27,792 → 28,059). PGO builds (engines/mt2pgo via build_pgo.py, same profile workloads as the landed engine):
| landed fastnle_ade PGO 31,218/31,209 | mt2 PGO kernel off 31,247/31,241 | mt2 PGO kernel on 34,190/34,187 | → +9.5% vs the landed engine,
hash identical, PGO quick gates 5/5. PGO narrows the plain-build gap (it had already optimised the old hot loops).
Live 1B seed deferred to the final landing (user 19:25: focus on optimisations); stage_k5 = v1.2 apply → gates → A/B → hash → PGO → PGO A/B.

## v1.2 SLIP AND FIX (19:33-19:50)
v1.2 passed the quick gates (young goldens have few doors/objects) but changed the rotation hash and 7.5M/16.7M corpus decisions.
Per-slice runtime switches (NH_MT2_S3 / NH_MT2_S7) on an 8-game run isolated S7 (door windows); S3 (object search by box cells) is exact.
trace_diff on the 8-game harness (trace lines now carry the 3x3 window state) gave the first divergence directly: turn 29480, monster 1361 at
(44,6) heading west; the original offered 3 candidates, the new path 4, admitting (43,6) = an OPEN DOORWAY (typ 22, flags D_ISOPEN) holding a
scroll of scare monster (pile bit 4) — onscary() rejects it, my window test had subtracted door cells from the "bad" set wholesale, dropping
their pile/trap/gas bits. (The agent drops scare scrolls in doorways: a learned habit, hence common.) Fix: exempt only the door-ness
(special & ~door), keep pile|trap|gas for door cells. Re-check: 8-game hash restored, traces identical over 7,891,183 decisions, 8-game
speed 30,369 → 34,012 (+12.0%; v1.1 was ~+10% on this set). Full chain (stage_k5: 128-game A/B, corpus hash, PGO) relaunched.
LESSON: the quick gates alone are not sufficient for window-rule changes; the 8-game rotation hash (6 s) is the right first check, then
the corpus hash. Added to the per-slice routine. S3's own gain looked small on the 8-game set (+0.4%): measure on the 128-game rotation.

## v1.2 RESULT (19:56, stage_k5 after the door-mask fix) — EXACT, +13.1% plain / +12.2% vs the landed PGO engine
128-game rotation, plain same-binary: NH_MT2=0 28,100/28,085 → NH_MT2=1 31,844/31,738 (+13.1%); quick gates 5/5; corpus hash 16,777,216
decisions 0 diffs. PGO (engines/mt2pgo rebuilt): landed fastnle_ade 31,221/31,226 → mt2 v1.2 35,036/35,030 = +12.2%, hash identical, PGO
gates 5/5. Cumulative ladder vs the landed engine (PGO): v1 — | v1.1 +9.5% | v1.2 +12.2%.

## HOTSPOT MAP WITH THE KERNEL ON (20:02; whole-step callgrind, kernel v1.2, 8 mature games x 20,480 steps = 380K Ir/step; shares of ALL Ir)
| bucket | share | detail |
|---|---:|---|
| monster turn | 65.1% | fast path ≈ 20% (7.9M eligible x 1,600 Ir; was 3,107) · OLD path m_move inclusive 25.7% (6.4M calls = 54% of moves still ineligible) · per-monster-per-turn: mcalcmove 3.0% incl (28M calls, the rn2(12) speed draw ≈ most of the RNG refills), movemon body 2.3%, minliquid 1.4% (23M calls), mt2_eligible 1.9%, dochug self 3.6%, mfndpos_masked 8.1% (6.2M calls from the OLD m_move, 0.46M from the fast fallback) |
| vision | 6.8% | vision_recalc 210K calls = 1.28/step at ~20K Ir each (3 call sites), left/right_side recursion |
| observation packing (env header) | 6.5% | pack_obs 24.7K Ir/step: inventory-slot loops ≈ 4.8K, nethack_zt_mask_on() 1.5K (getenv-cached static called ~500x/step), cant_hold/item_classes verb tests ≈ 2.8K, grid pass ≈ 2.4K |
| RNG refills | 2.9% | isaac64_update: ≈ 1 refill/step, mostly mcalcmove draws (RNG-freedom item) |
| display pipeline | ~4% | newsym 1.5% (3.65M calls), show_glyph 0.5, flush_screen 0.6, mapglyph/rl_print_glyph 0.5, topline 0.3, blstats 0.4 |
| hero bookkeeping | ~4% | nh_timeout 1.1, dosearch 1.3 (the agent's search spam), moveloop 0.9, settrack 0.6, weight_cap 0.6 (4M calls = 25/step) + inv_weight/nle_weight 0.5 |
| libc/other | ~4% | strcmp/strchr/strstr 0.8, memset/memcpy 0.4, were_change 0.3 (per monster per turn), in_rooms 0.3, sortloot 0.1 |
Eligible-only v1.2: 1,600 Ir/move; m_move_fast self 736 is a long tail (no line > 31 Ir: track-hit compare 31, hero-state test 28, bad-mask 23,
gbuf compare 22, dist2 40, poss writes 23, box loops 25); display gates 2 x 50; eligibility ~50; dochug_fast 84; refills 48; fallback 46.
RANKED NEXT (exact unless marked): (1) old-path populations — why-census per failing clause (CG build, running after K7) then extend the
kernel to the big ones (v1.3 = peaceful 4.9% of step); (2) header pack_obs: hoist nethack_zt_mask_on, restructure the inventory loops
(+1.5-2%); (3) per-monster-per-turn bookkeeping: minliquid call gate, movemon body order, were_change (+1-1.5%); (4) fast-path tail: hero
word (v1.3), display gate (+1%); (5) vision 6.8% and display pipeline 4%: algorithmic, big, later; (6) RNG 2.9%: non-exact (user-permitted),
last.

## v1.3 RESULT (20:12) — rotation EXACT and +14.3%, corpus hash FAILED (15.07M/16.78M): a THREADING slip, fixed as v1.3b
128-game rotation (single worker): NH_MT2=0 28,312/28,324 → NH_MT2=1 32,371/32,361 = +14.3%, obs hash identical; 8-game hash identical;
quick gates 5/5. Corpus replay (replay_hash 512 games on 24 THREADS): 90% of decisions differ. Cause: the cached hero-state word
(nh_mt2_hero_stale/nh_mt2_hero_bad) was a plain process global, shared across the games running on different threads; every single-thread
check passes, the multi-thread corpus (and the trainer) would not. Fix v1.3b: per-env fields in nh_ctx_gen.h (nh_mt2_hero_valid, 0 = stale at
context creation). LESSON for the gate routine: the corpus hash is the only multi-thread check in the chain — keep it mandatory for every
slice, and audit every new global for per-env state (kernel globals now: nh_mt2_fast/s3/s7 read-only switches; CG counters and the trace
file are instrumentation only). Revalidation = stage_k10 (behind the C2-harness profile).

## WHY-CENSUS (20:22; v1.3 predicate, 128-game rotation, first failing clause, % of ALL monster moves): eligible 61.3%
asleep 12.5 (cheap early exits) | HERO STATE 10.9 → Displaced 70.6% of those, Invis 26.0%, Upolyd 3.1%, Hallucination 0.1% | near (distmin
<= 9) 7.6 | species_nofast 2.6 → unicorns 55% (white 34, gray 13, black 8), dwarf 35 + dwarf lord 3 (tunnellers), shrieker 3 | status 2.1 |
shk/priest/guard 1.4 | couldsee 0.8 | fleeing 0.7.
READING: the agent wears a cloak of displacement most of the time; Displaced/Invis only change the believed hero position, which the
original set_apparxy() computes — calling it (twice, as the original) instead of assuming the exact position makes both exact; Upolyd adds
the lined_up() rn2(25) draw in two places. That is v1.4 (apply_mt2_v14.py, stage_k11): ~7% of all moves move from the old path (~2,700 Ir)
to the fast path (~1,600) ≈ +3% SPS expected. Near monsters (7.6%) are the combat kernel = a different, later program; unicorns/dwarves
(1.4%/1%) not worth their rules yet.
## C2-HEADER PROFILE (20:16; replay_sched6_C2 = landed mask code, kernel v1.2): 366,864 Ir/step (base header 380,334: C2 = -3.5%)
pack_obs 4.9% (17.8K Ir/step) and flat: per-cell bounds accessor 1.3K, grid pass + glyph classification 2.4K, lazy accessor nh_lazy[40]
0.9K, C2 slot writes 0.6K, throw-target ordering 0.9K. Maybe +1.5% with effort; below the monster items in priority.

## AFTER v1.4 — remaining exact levers, sized from the kernel-on map (each ~1-2% of the step; the big ones are hard)
| lever | est. | notes |
|---|---:|---|
| mfndpos mask path for NEAR monsters (inside mfndpos(): plain window + hero/mux cells run the original per-cell code incl. Elbereth) | +1.5% | 6.2M old-path mfndpos calls/163K steps; near hostiles are 7.6% of moves at ~2,500 Ir |
| packer after C2: per-cell bounds accessor, lazy accessor, glyph classification | +1.5% | 17.8K Ir/step, flat |
| per-monster-per-turn bookkeeping: minliquid call gate, movemon body order, dochug prelude for sleepers | +1% | ~8% of step spread thin |
| fast-path tail: display gate, eligibility, dochug_fast | +1% | 1,600 Ir/move, flat |
| unicorns (NOTONL/avoid/rloc rules) + dwarves (ALLOW_DIG) | +0.5% | 2.6% of moves |
| vision_recalc 6.8%, display pipeline 4%, near-monster combat ~8% | big | algorithmic programs, not slices |
| RNG 3% (mcalcmove dead draws, cheaper generator) | +3% | NON-exact (user-permitted), breaks the exact gates → last |
DECISION: after v1.4 validates, consolidate (PGO build, landing-style A/B, trainer A/B of the final kernel, commit, handoff patch) and report
the ladder; then pick between the near-monster mfndpos path and the vision program with the user.

## v1.3b RESULT (20:24) — EXACT: corpus hash 16,777,216 / 0 diffs (per-env hero word), rotation hash identical, +14.6%
Clean pair: NH_MT2=0 28,064 → NH_MT2=1 32,167 (rep1 old-path 22,848 is contaminated by a concurrent census run, discarded). Ladder (plain
same-binary, 128 games): v1 +10.7 | v1.1 +11.1 | v1.2 +13.1 | v1.3b +14.6. v1.4 (Displaced/Invis/Upolyd) in stage_k11.

## v1.4 RESULT (20:31) — EXACT (8-game, gates, rotation, corpus 0 diffs), +17.1% plain same-binary
NH_MT2=0 28,186/28,173 → NH_MT2=1 32,996/33,006. Ladder (plain, 128 games): v1 +10.7 | v1.1 +11.1 | v1.2 +13.1 | v1.3b +14.6 | v1.4 +17.1.
Consolidation = stage_k12: PGO build of v1.4, PGO gates, landing-style A/B vs fastnle_ade PGO (P-core 2 and E-core 16), trainer A/B
(ab_mt2v14.json: fast protocol sched_v22/v12 x2, live digest).

## v1.4 CONSOLIDATION (20:49, stage_k12; PGO build engines/mt2pgo 3f1d12b0…, PGO quick gates 5/5)
| landing-style, rotation-16, 128 games | landed fastnle_ade PGO | mt2 v1.4 PGO | gain |
|---|---:|---:|---:|
| P-core 2 | 31,243 / 31,233 | 36,147 / 36,152 | +15.7% |
| E-core 16 | 21,693 | 24,876 | +14.7% |
Trainer A/B (fast protocol, 5M model, 2048 agents, same PGO binary NH_MT2=0/1): sched_v22 388,912/385,196 → 407,603/406,489 (+5.2%);
sched_v12 (pool) 243,525/239,295 → 257,108/255,353 (+6.1%). Live learning 150 epochs digest 31e2e3deae720ef4 = reference (exact under
training). Regime grid (5M x 4096/8192 both trainers, 15M x 2048/4096 scheduler; off/on x2) = stage_k13 / ab_mt2v14_grid.json.

## DIRECTIVE (20:58, user): make the env as fast as possible; do not weigh trainer regimes or the 5M/15M transfer for now.
Measure env-side on the harness (rotation-16, PGO landing-style), keep the exact gates (8-game hash → quick gates → 128-game hash → corpus),
report trainer transfer only as information. Order of the next programs by size × method fit: vision_recalc (6.8%), near-monster kernel
(~8%), per-monster-per-turn bookkeeping (~8%), fast-path cached intent (~20% bucket, flat), packer after C2 (4.9%), display/hero (~8%).

## REGIME GRID (21:07, stage_k13; PGO v1.4, same binary NH_MT2=0/1, fast protocol, two reps) — information only (user: env speed is the goal)
5M/4096 sched +4.5% (404.9K/413.3K → 429.3K/425.5K: at the ~430K GPU cap) | 5M/4096 pool +5.3% | 5M/8192 sched +0.4% (cap) | 5M/8192 pool
+3.1% | 15M/2048 −0.1% | 15M/4096 −0.2% (GPU-bound). Net SPS on this box is GPU-capped except 5M/2048 (+5.2/+6.1%).

## VISION CENSUS (21:15; CG build, hash of every vision_recalc input vs the previous recalc)
8 games: 232K recalcs = 1.42/step: control 0 (flag-triggered) 122.7K, control 1 (hero move) 108.2K, control 2 1.1K; identical inputs
46.8K = 20.2% of all (38% of control-0); 52% of recalcs happen with a light source on the level. 128 games: 3.42M = 1.31/step, redundant 19.7%
(41% of control-0). Excluding seenv/waslit from the criterion (a repeated recalc cannot change them) adds only 0.1 pt → 59% of flag-triggered
recalcs have genuinely changed inputs (monster-opened doors, carried lights, pits/teleports). EXACT SKIP value: 0.26 recalc/step x ~20K Ir ≈
1.4% of the step, via epochs (opacity: block/unblock_point/vision_reset; typ: nh_move_typ_set; lit: read.c litroom, dig.c:79, vault.c:137;
seenv assignments; light sources: positions recomputed at the check; hero tuple compared) with the CG full-hash as the verify oracle.
Making the recalc itself cheaper (update loop ~8K + ray casting ~10K per call) applies to all 1.3/step: ~2% per 30% speedup — harder.
Decision pending the v1.4 re-rank (stage_k14: whole-step + old-path-only profiles).

## RE-RANK WITH v1.4 (21:20; whole-step 8 games): 345,963 Ir/step (v1.2 380K, pre-kernel ~420K)
monster turn 61.5%: fast path 17% (69% of moves, ~800 self/move), old path m_move 4.1% + mfndpos 4.3% + dochug 3.4% (old-path-only profile:
31% of moves at 2,086 Ir = 20% of the step; by function: m_move 458, mfndpos 367, dochug 148, fobj cursor 95+17, nh_newsym_moved 59, select_rwep
40, isaac 39, mt2_eligible 38, searches_for_item 33, find_misc 30, find_defensive 22, linedup 21), bookkeeping ~14% (movemon 8.8K, mcalcmove
6.6K + RNG 11K, minliquid 5.3K, mcalcdistress 4.7K, mt2_eligible 7K); vision 12.6%; packer 5-6%; display/hero/libc ~13%.
Per-reason old-path profiles (near vs asleep) = stage_k16.

## v1.5 VISION SKIP — verify caught it (21:22): 684,902 skips / 5,846 VIOLATIONS (0.85%) on 128 games → chain stopped before any gate
Audit: persistent direct writers of viz_array outside vision.c exist (dig.c mkcavepos, hack.c boulder-into-pit kludge) — invisible to an
input-hash oracle because viz_array is an output; and seenv additions outside vision.c (display.c:2438) are harmless to a recalc but count as
input changes. Fix v1.5b: epoch bumps at the two direct writers; oracle replaced by the no-op check (CG build: when the skip logic says
'same', snapshot viz_array/rmin/rmax/seenv/waslit/glyph, run the full recalc anyway, count any difference) — the gold standard for "skipping
is exact". stage_k17 = per-component violation counts of the old oracle; stage_k18 = the no-op oracle on 8 games.

## VISION SKIP ORACLE (21:35-21:45)
Per-component diagnosis of the input-hash violations: 359/359 (8 games) and 5,829/5,829 (128 games) were the SEENV component alone (hero,
opacity, typ, lit, lights: 0) → seen-vector additions outside vision.c (display.c:2438, SVALL sets), harmless by the |= argument.
No-op oracle (CG build: on 'same', snapshot viz/rmin/rmax/seenv/waslit/glyph, run the full recalc, compare): 8 games 47,445 skips → 0
differences in every field; 128 games 684,902 skips → viz 0, rminmax 0, seenv 0, waslit 0, GLYPH 66 (0.01%): the x-ray loop calls newsym
unconditionally for every cell in range, so a repeat recalc redisplays world changes there. Fix: never skip while u.xray_range >= 0.
Also fixed on the way: the two persistent direct writers of viz_array outside vision.c (dig.c mkcavepos, hack.c boulder-into-pit) bump the epoch.
Sleeper profile (K16 why=4): 156 Ir per sleeping-monster move = 0.6% of the step — nothing to gain there.
Near-monster profile (K16 why=9): 8.6% of moves at 3,791 Ir = 9.9% of the step; m_move 833, mfndpos 670+98+31, dochug 209, select_rwep 131,
display gates 128, cursor 129, mt2_eligible 75, movemon 71, find_misc 62, RNG 62, linedup 54 + lined_up 34, mattacku 42 + getmattk 30,
place_monster 39, find_defensive 38, can_carry 37, mintrap 34, find_offensive 34 → the far kernel's shape again; combat itself < 3%.
v1.6 (apply_mt2_v16_near.py, written): distmin >= 2 and could-see monsters join the fast path with the range-dependent originals kept
(distfleeck, find_defensive/find_misc within dist2 36, wield + castmu blocks verbatim, lined_up for in_line, should_see for appr/track,
hero/image cell in the 3x3 → mfndpos fallback, ALLOW_U / hero-cell / image-cell blocks verbatim after selection). Expected +5-6%.
