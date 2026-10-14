# Engine line-level campaign (14 Oct 2026) — from the perf annotate map to bit-exact rewrites

Source of truth: /puffertank/docker/perf_rot/results/annot16b.* (host perf record, rotation 16 on one P-core, tile_signed_pgo engine, harness
replay_sched6 256 games; 99K cycles + 99K branch-miss samples; line attribution via a -g twin build with identical machine code:
engines/tile_signed_pgo_g, profiles renamed to the twin's build path). Scripts: perf_rot/annot_script.py (perf script -> addr2line -i aggregation).

## Line-level findings (share of the function's samples; function share of all cycles / mispredicts in brackets)
m_move [23.6% / 29.4%]: candidate-selection loop monmove.c:1307-1336 incl. nh_move_position_bit (11.4% of m_move mispredicts, branchy range
check), dist2/nearer compare and the take/no-take branch at 1326 (7.2%+3.9%+3.5%+3.2%), should_displace 731-745 (6.7%). ~43% of m_move's
mispredicts (12.6% of ALL mispredicts) and ~28% of its cycles (6.6% of all) sit in this <= 9-iteration loop.
mfndpos_masked [13.9% / 12.8%]: pool/lava test mon.c:1930 + nh_cell_pool/isok 1735-1746 = 32% of its mispredicts, 13% of its cycles;
diagonal/door block 1919-1929 = 13% of mispredicts; rock/bars 1897-1907 = 9% / 11%.
nethack_pack_obs [7.4% / 8.8%]: NOT the grid scan (lines 651-683 = ~10% of it). nethack_compute_mask + nethack_slot_usable + zt_blocked +
ray_target = ~65% of the function (4.8% of all cycles): per-(verb, slot) predicate calls, zt check per call, O(n^2) WIELD weld scan.
movemon: dochugw + dmonsfree; nh_fobj_next: SIMD scan 926-932; dochug: disturb/distfleeck; newsym: display.c 760-915.

## Plan
A. m_move selection loop: branchless nh_move_position_bit, branchless take/select (RNG draw order preserved), branchless min in should_displace.
B. A + mfndpos prefilters: pool/lava/drawbridge/door column masks (set in nh_move_typ_set), diagonal block mask, worm-cross via occupied mask.
C. compute_mask restructure (env header; trainer + harness builds).
Gates: check.py --quick (34 goldens + 26 fuzz + status + interleaved + shuffled), full every-action corpus hash (16.7M decisions), native
rotation-16 harness A/B on cpu 2 (obs hash identical), perf record of the candidate (mispredicts must drop where predicted), trainer 5M/2048 A/B.

## 2026-10-14 08:44 — stage 1 results (native rotation 16, one P-core (cpu 2), 128 games, warm 4096 / measure 16384, same obs hash 7a111519e889cf75 in all six runs)
base 29,497 / 29,525 sps | selA 30,653 / 30,536 (+3.6-3.9%) | selB 30,652 / 30,655 (+3.8-3.9%; +0.0-0.4% over A, within the ~0.4% run-to-run spread).
Full every-action corpus: selA 16,777,216 decisions 0 different; selB 16,777,216 decisions 0 different. Quick gates 5/5 both.
Reading: the m_move selection-loop rewrite (A) is real and bit-exact; the mfndpos mask prefilters (B) buy little on top — either the pool/lava
mispredict samples were skid from neighbouring branches, or PGO had already laid those out cheaply; B's own perf record (stage 2) decides.

## 2026-10-14 08:53 — stage 2: candidate C native + candidate B perf record
C (mask header, base engine, harness replay_sched6_C): base 29,494 / 29,496 vs C 29,874 / 29,881 = +1.3% per step, obs hash identical.
selB perf record (same harness/argv as annot16b, 256 games: base 29,289 sps / selB 30,493 = +4.1%, obs hash 3bff914ab1ecb61e identical):
total branch-misses −11% at equal cycles (−14% per step); m_move cycles −10.0%, m_move mispredicts −36.9% (the selection loop was the
predicted 43% of its mispredicts); mfndpos cycles +1.8%, mispredicts −6.5% → the pool/lava/diagonal mispredict samples were skid from
neighbouring branches (loop exit, continue tests), and the per-call mask preparation (4 extra neighbour masks, 2 cache lines of columns)
costs what the removed per-candidate tests saved. B = null increment over A; A is the keeper, B parked (harmless, same speed).
Secondary: isaac64_update +10% share (more RNG per unit time = more steps per unit time), nh_fobj_next −6.7%.

## 2026-10-14 08:57 — stage 3: trainer A/B (5M/2048, sched_v12 config: PUF_SCHED=1 slots 4 cap 12 batched gather pw 1.25, 24 pinned workers; two interleaved series)
base 388.8K / 367.4K | selA 388.6K / 384.7K | selB 384.3K / 384.6K | selB + C header (sched_v13) 387.5K / 385.5K.
BATCH_PROOF obs hash identical in all 8 arms (b88357407e520673, 44 epochs) → bit-exact at the trainer level.
SCHED_STATS us_per_step (wall per step per worker): base 57.5 / 57.9 → selA 56.0 / 55.9, selB 56.1 / 56.6, selB+C 56.6 / 55.8 = −2.5..−3.5% per step.
SPS noise (base 388.8 vs 367.4 in the same session) is larger than the effect; the per-step metric carries the signal. Expected trainer gain from
+3.8% engine (native) is ~+3% SPS; 2-rep A/B cannot certify beyond "consistent with". Keeper set: A (engine) + C (header); B parked.

## 2026-10-14 09:13 — stage 4/5: clean C series, twins, B line map, candidate D
C clean (quiet box): base 29,505 / 29,299 vs C 29,871 / 29,857 (+1.2..+1.9%); obs hash identical. Twins selA_g/selB_g: machine code identical.
B line map (perf_rot/results/annot16_selB.lines.txt): m_move's remaining mispredicts lead with the track-avoidance inner loop (monmove.c
for j<jcnt ... rn2(4*(cnt-j)): 10% + 2.6% + 1.7%), rn2 refill 6%, the trackmask hit test (skid onto position_bit) 7%; mfndpos: loop exit/cnt++
(skid) ~14%, trap-presence load 6.6%, rock test 5.5%, worm-cross guard 4.4%, bad_rock (tight squeeze) 3.7%, Displaced test 3.7%.
D (= A + itsstuck identity-first reorder): base 29,495 / 29,496 | selA 30,663 / 30,658 | selD 30,689 / 30,687 → D +4.05%, A +3.95% (harness
repeatability 0.01%). Full corpus selD 16,777,216 decisions 0 different; quick gates 5/5.

## 2026-10-14 09:19 — stage 6: live learning proof (weights updating, live sampled actions, 150 epochs, 2048 agents, 4 buffers, sched_v12 / v13)
LIVE_PROOF per-epoch observation hashes: see stage6.log (base vs selD vs selD + C header). Live SPS 421.4K / 421.5K / 418.5K (young-game regime).

## 2026-10-14 09:29 — stage 7: candidate E (= D + track-match mask in m_move + squeeze mask in mfndpos)
base 29,514 / 29,495 | selD 30,687 / 30,692 | selE 30,915 / 30,905 → E +4.77% per step (D +4.05%, A +3.95%); obs hash identical; quick gates
5/5; full corpus 16,777,216 decisions 0 different. E is the keeper; landed (amended) in the fast-nle backup worktree.
Live learning proof (stage 6, D + C): per-epoch observation hashes identical to base for all 150 epochs (digest 31e2e3deae720ef4).
Diminishing returns reached: remaining m_move/mfndpos items in the line map are each < 1% (object-search loop, monhaskey, trap/pile summary
loads, loop-exit mispredicts), several were parked null by the 2026-10-08 campaign (trap bitmaps, glyph memo). Stop here for the engine.

## 2026-10-14 09:32 — stage 8: landed fast-nle source (backup worktree commit e038efa41 = A+D+E on mt7+dv4+tile_signed) built LTO and gated
fastnle_check gates rc=0 6 passes HASHES lines_fastnle_check 16777216 0 09:31:44
Campaign closed. Keepers: engine A+D+E (+4.8% per step, fast-nle backup commit e038efa41), mask header C (+1.3%, pufferlib backup commit 1803a82c).

## 2026-10-14 13:13 — LIVE 1B SEED under gdb on the landed engine (fast-nle e038efa41 = A+D+E, PGO build engines/fastnle_ade): seed 3001, champion
config and stack (cohort_d8), exited normally after 80 min / 3814 epochs, last inline score 10,039.6 (same seed on tile_signed_pgo: 9,714.6, 81 min;
inline eval noise ±1000 and biased low). Quick gates 5/5 on the PGO build. The mt7-landmine rule is satisfied; the engine change can ship.
Artifacts: /puffertank/docker/champion10_20261011/ade/s3001_ade/{run.log,gdb.log,checkpoints}, PROVENANCE.txt.

## 2026-10-14 16:35 — engine round 2 (user: "keep pushing engine speed")
Leads: (1) isaac64_reseed 0.7% is per-episode init (isaac64_init / nlernd time_rng), not per step — nothing there; nle_rng_state() is an
exported accessor called per rn2 (not inlined by LTO) → F inlines the ctx read in rn2/rn2_on_display_rng. (2) E-core tune: PGO builds with
-mtune=gracemont / -mtune=alderlake vs default tune, rotation-16 harness on cpu 16 (E) and cpu 2 (P), 2 reps (tune.sh / tune.log). (3) Action
mask C2: per-slot facts once per step + per-verb 64-bit mask ops instead of per-(verb, slot) predicate calls (apply_C2.py; headers/*; harness
replay_sched6_C2; trainer sched_v22) — exact by construction; validated by the live digest 31e2e3deae720ef4 and native rot16 vs C.
(4) F = E + rn2 accessor inline + nh_mover_scary vampire-before-altar reorder + Displaced&&monseeu hoisted out of the candidate loop (exact).

## 16:52 — core-type tune: NULL. Rotation-16 harness, landed engine (fastnle_ade) PGO builds: E-core (cpu 16) default 21,668 / 21,683,
-mtune=gracemont 21,668 / 21,674, -mtune=alderlake 21,619 / 21,640; P-core (cpu 2) default 31,242 / 31,244, gracemont 31,142 / 31,139,
alderlake 31,122 / 31,127. PGO fixes the layout; the tune flag changes nothing useful. Per-core-type engine dispatch: closed. Next codegen lever:
BOLT post-link layout (instrumentation mode; needs -Wl,-q relocations in the link) on top of PGO.

## 17:05 — C2 (action mask restructure) KEEPER, landed
Native rot16 (cpu 2): base 29,518 / 29,512 | C 29,895 / 29,919 (+1.3%) | C2 30,672 / 30,639 (+3.9% over base, +2.5% over C); obs hash unchanged.
Trainer (sched_v22 = v12 + C2 header): live digest 31e2e3deae720ef4 EXACT (150 epochs, weights updating); fast 5M/2048: v12 380.8K / 380.1K vs
v22 385.8K / 385.1K (+1.3%, both reps). Landed in the pufferlib backup worktree on top of C (patch handoff/C2_over_C_header.patch).

## 17:12 — candidate F (rn2 accessor inline, scary reorder, Displaced hoist): NULL. selE 30,918 / 30,936 vs selF 30,934 / 30,955 (+0.05%);
exact (quick 5/5, corpus 0 diff) but inside the 0.1% repeatability → not landed (keeps the engine commit minimal). Micro-items are exhausted.

## 17:30 — BOLT post-link layout on top of PGO: NEGATIVE, closed. fastnle_ade 31,246 / 31,233 | same source rebuilt with -Wl,-q (fresh PGO
profile) 30,966 / 30,966 (−0.9%: profile/layout jitter between PGO builds) | BOLT (ext-tsp blocks, hfsort+ functions, split functions/cold,
icf, instrumentation profile from the rot-16 harness) 30,132 / 30,141 (−3.5% vs ade, −2.7% vs its own input); E-core 21,708 → 21,092 (−2.8%).
Exact (quick 5/5, corpus 0 diff). BOLT's layout undoes PGO's on this code; lite mode profiled 2,309 of 4,683 functions. Not pursued further.
Codegen levers now exhausted: PGO (kept), LTO (kept), -mtune (null), BOLT (negative).
