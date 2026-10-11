---
name: nethack-elbereth-forensics
description: "ELBERETH verb forensics 2026-08-06: obs sensor dead (internal[6]=0 hardcoded), ~61% of E-attempts refused (41% levitating, 20% swallowed), wards DO form when normal; fix package = sensor export + legality mask"
metadata:
  type: project
---

ELBERETH (verb 6) existed and policies use it hard (15-38 engraves/ep, 31% at
hp<33% with hostiles adjacent = genuine crisis deployment). NH_ENGRLOG forensics
(zba_s301, 554K events) found three stacked problems:

1. **DEAD SENSOR**: winrl.cc ships `obs->internal[6] = 0 /* used to be disp
   seed */` — the "any engraving"/"active Elbereth" obs features have been
   CONSTANT ZERO for the project's entire history. Policies engrave blind;
   ~16% of attempts land on an already-active ward (compulsive re-engraving).
   FIXED IN MAIN 2026-08-06 19:35: winrl.cc exports ward(0/1/2) | 4*engulfed;
   env pack strips bit 2 (extra[0]=&3); ELBERETH legality-masked while
   levitating (cond & 0x400) or engulfed. Goldens 34/34, no-globals OK,
   gradcheck PASS. First arm on fixed env: fscfix_s301 (group fscfix).

2. **61% of E attempts are engine-refused free actions**: 41% while LEVITATING
   ("can't reach the floor/ground"), 20% while SWALLOWED. Both states make E
   (and much else) useless; E-spam there wastes agent steps at the exact
   moments that kill (being digested / floating helpless). Legality-mask
   candidates (sanctioned by mask-for-legality rule): mask ELBERETH when
   levitating or engulfed.

3. **Levitation-lock**: heavy levitation time (cursed boots era; cursed_worn
   0.14-0.30) — levitation ALSO blocks stairs-DOWN and pickup, a hidden depth
   blocker. Levitation IS visible (condition bit BL_MASK_LEV 0x400, encoder
   expands 13 cond bits) but the escape behavior (takeoff boots) appears
   unlearned. Worth its own census: fraction of game-time levitating, and
   whether DOWN-blocked-by-levitation correlates with shallow episodes.

Normal-state engraves mostly succeed (empty-msg completions; wards form).
The macro flow itself is fine.

**Tooling gotchas burned into this investigation**: build.sh only builds
libnethack.so IF MISSING — `rm build/libnethack.so` (or wipe build/) before
any vendor edit or it silently no-ops (bit twice). Worktree-copied vendor
needs its build/ dir wiped (CMakeCache pins the original path). wt_engr
worktree carries the working sensor + NH_ENGRLOG/ENGRPOST traces.

**ARC CLOSED 2026-08-06 20:04 — warding is NOT the missing competency.**
Ceiling probe (paired ctl/forced evals, wt_engr, override = engrave+hold at
hp<33% & adj>=1): fsc 7279->6529 = -750, zba 6495->6213 = -282, death_combat
UNCHANGED (0.805->0.805). Forced warding saves no fights, burns income time —
a Monk's crisis move is win-the-fight or flee, not ward-and-camp; autoascend's
Elbereth value rides on threat-selection judgment we did not test for. Per
pre-registered rule (prize<=0): NO adoption mechanics (no crisis-eps, no ward
reward). Sensor fix + legality mask stay as hygiene.
fscfix_s301 (fsc config on fixed env): certified 6274/depth 5.91, engraves
0.05/ep (verb never bootstrapped post-mask), death_adj 1.10 (unchanged).
-896 vs fsc_s301 is single-seed-vs-single-seed inside +-443 population SD —
NOT attributable to the fix without replicates; but it flags fsc_s301 7170 as
possibly a lucky draw (cf zbf 7023->6790, rcminf best-of-8 7123 vs mean 6380).
fsc-family true mean = the open question; replicates on the fixed env decide.
NOTE: E-spam-while-stuck was a zero-game-time no-op that burned step budget;
masking it shifts action distribution in stuck states — watch for no-op
migration to other refused-free verbs (pickup while levitating etc.).

VENDOR BUILD GOTCHA — EXACT MECHANISM (bit me again 2026-08-12, cost one
wasted 250M run): build.sh only builds the engine when
vendor/fast-nle/build/libnethack.so is ABSENT — source edits NEVER trigger
a rebuild. After ANY vendor edit run:
  cmake --build vendor/fast-nle/build --target nethack -j$(nproc)
and confirm the "Building CXX object ...<file>.o" line prints. Also: a
flag-validation hash comparison is only valid MATCHED-COMMAND (same run_id/
flags, env var the only delta) — eval_episodes/run_id in the command change
the checkpoint hash vs the fpgate REF form.

**2026-08-15 LEGALITY PROBE — NOT A GAP, and the old sensor bug is FIXED.**
scratchpad/elbprobe.c on champion s311, 8 eps/role, danger := hp_frac < 0.35
AND an adjacent non-peaceful monster:

| role | ELB legal | used /1k steps | danger steps | legal in danger | used in danger |
|---|---|---|---|---|---|
| Archeologist | 99.9% | 10.8 | 68 | 100% | 23.5% |
| Tourist | 100% | 28.7 | 106 | 100% | 27.4% |
| Healer | 99.7% | 27.1 | 162 | 100% | 20.4% |
| Ranger | 99.8% | 7.4 | 79 | 100% | 27.8% |
| Valkyrie | 98.2% | 3.4 | 34 | 100% | 23.5% |

ELBERETH is legal in 98-100% of steps and **100% of danger steps** — no mask
problem. The engrave sensor is ALIVE (internal[6]&3 reaches 2: 174-868 active
readings per run), so the "dead sensor internal[6]=0" bug recorded above is
fixed in the current build. Every role uses it in ~20-28% of danger steps —
strikingly uniform, and NOT the "weak roles never engrave" story the census
suggested (that was elb per 1K TURNS; Arc's turn count is tiny because
digging is multi-turn, so per-turn and per-step rates invert).

**The real datum: danger is RARE — 0.2-2.2% of steps.** Episodes do not pass
through a long low-HP window before ending, so reactive panic tools have
little opportunity by construction. That points away from Elbereth/prayer/
healing fixes and toward either avoiding the engagement or raw HP capacity.
**How to apply:** stop treating "weak roles don't use X" claims from per-turn
census rates as behavioural gaps — normalise per STEP and probe legality
first. See [[nethack-weapon-diagnostic]], [[nethack-kit-audit]].

**2026-08-23 correction**: engrave-state sensor measured ALIVE on the current tree (extra[0] nonzero ~5-9% of steps in 1B-policy rollouts) — the dead-sensor finding is stale or the fix landed; re-verify before citing.
