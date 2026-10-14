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
M2 non-monster census: hero action, vision/display, timers/regen, obs export, RNG, moveloop bookkeeping.       STATUS: pending
M3 redundancy census: callee call counts per monster move (couldsee/cansee, in_rooms, m_carrying, dist2, onscary, SPWQ) → recompute share.
                                                                                                           STATUS: pending
M4 game-turn structure: game turns per env step; monsters moved per turn by depth (corpus).                    STATUS: pending
M5 hardware view at production rotation (12) on P and E cores: cycles / mispredicts / L1d / L1i per function (host perf server needed).
                                                                                                           STATUS: pending (server down)
## Design (written only after M1-M5)
- Prize bound by situation, with the assumption behind each number.
- Representation (per-cell planes, SoA monster fields) sized to the dominant decisions; who maintains each plane.
- Validation harness: decision-kernel equivalence over the corpus (candidate set + choice probabilities), specified before engine code.
- Milestones with go/no-go measurements, effort, stop rule; non-goals (special monsters on the old path; display semantics untouched).
