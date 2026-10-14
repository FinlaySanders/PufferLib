# Handoff: bit-exact engine and action-mask speedups from the line-level perf map (14 Oct 2026)

Evidence and method: ../PROGRAM.md (ledger), perf_rot/results/annot16b.* and annot16_selB.* (line attribution), stage*.log (gates and timings).

## Patches
- A_engine.patch — fast-nle engine (applies to the fork lineage at backup/nethack-optimizations-20261008, e4d8e6e8f): m_move candidate
  selection without data-dependent branches (same predicate, same rn2 draw order), branch-free nh_move_position_bit, branch-free min in
  should_displace. Native +3.95% per step at rotation 16; m_move mispredicts −37%, total −14% per step.
- D_over_A.patch — itsstuck: identity test before the hero attack-table walk (pure reorder). +0.1% on top of A.
- E_over_D.patch — m_move track avoidance as a 4-wide match mask visited in ascending order (same rn2 draws); mfndpos tight squeeze reads
  the two orthogonal cells from the nonrock mask for movers without tunnelling/wall-passing/Sokoban rules. +0.7% on top of D (total +4.8%).
- C_header.patch — pufferlib ocean/nethack/nethack.h: zero-time block set as per-verb slot bitmasks computed once per step; the per-slot
  WIELD weld rescan removed (the caller's gate implies it). Native +1.3% per step. Applies to the working tree and the backup branch.
- (parked) candidate B mask prefilters in mfndpos: null increment, see PROGRAM.md.

## Proofs
- 34 goldens + 26 fuzz + status/interleaved/shuffled gates: pass (A, B, D).
- Every-action corpus 16,777,216 decisions: 0 different (A, B, D, E).
- Native harness (replay_sched6, 128 and 256 games): observation hashes identical to the base engine.
- Trainer fast protocol 5M/2048, 44 epochs: BATCH_PROOF observation hashes identical across base / A / B / B+C (8 arms).
- Live learning (weights updating, live sampled actions, 150 epochs, D + C): identical per-epoch hashes for all 150 epochs.

## Landing checklist (per the mt7 landmine): one live 1B seed under gdb before the engine change ships; rebuild PGO with the standard
profile workloads (build_pgo.py reproduces the tile_signed_pgo recipe).
