#!/bin/bash
# Perf phases, third attempt: anchored full-path patterns (a long-lived host process also matched the loose pattern), G1 + G3 only.
source /puffertank/experiments/nethack-scheduler-20261012/overnight/lib.sh
L=$X/overnight/LOG3.txt; log "=== OVERNIGHT-3 START"
PGO=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build; PLAIN=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed/build
PAT='^/puffertank/experiments/nethack-scheduler-20261012/replay_sched6 128 1 4096 16384'
TPAT='^/puffertank/experiments/nethack-24h-20261009/binaries/sched_(ctrl|v10) train'
wait_daemon 600 || { log "daemon down; abort"; exit 1; }
perf_req sanity_rot1 "$PAT" stat "$G1" 20 10 && { rot_run 1 $PGO sanity_rot1; perf_wait sanity_rot1; }
grep -qE '[0-9,]+\s+cpu_core/cycles/' $D/results/sanity_rot1.txt || { log "sanity: no cpu_core cycles counted; aborting"; exit 1; }
log "=== PHASE A: rotation perf matrix (G1, G3)"
for A in 1 4 16 64; do for G in G1 G3; do ev=$G1; [ $G = G3 ] && ev=$G3; perf_req rot${A}_$G "$PAT" stat "$ev" 45 15 && { rot_run $A $PGO rot${A}_$G; perf_wait rot${A}_$G; }; done; done
log "=== PHASE B: PGO vs plain engine, rotation 1 and 16"
for A in 1 16; do for G in G1 G3; do ev=$G1; [ $G = G3 ] && ev=$G3; perf_req plain_rot${A}_$G "$PAT" stat "$ev" 45 15 && { rot_run $A $PLAIN plain_rot${A}_$G; perf_wait plain_rot${A}_$G; }; done; done
log "=== PHASE G: per-event sampling profiles, engine rotation 1 / 12 / 16"
REC_EV='cycles:u,branch-misses:u,L1-icache-load-misses:u,L1-dcache-load-misses:u'
for A in 1 12 16; do perf_req prof_rot${A} "$PAT" record "$REC_EV" 45 15 && { rot_run $A $PGO prof_rot${A}; perf_wait prof_rot${A} 600; }; done
log "=== PHASE C: trainer perf pool vs scheduler (5M/2048, 120 epochs) + profiles"
for arm in perf_pool perf_sched; do for G in G1 G3 REC; do
  ev=$G1; mode=stat; [ $G = G3 ] && ev=$G3; [ $G = REC ] && { mode=record; ev=$REC_EV; }
  perf_req ${arm}_$G "$TPAT" $mode "$ev" 50 25 || true
  ( cd $H && rm -rf runs/${arm}_$G && sed "s/\"${arm}_G1\"/\"${arm}_$G\"/" $X/overnight/ab_${arm}_G1.json > $X/overnight/ab_${arm}_$G.json && python3 campaign_ablate.py $X/overnight/ab_${arm}_$G.json 2>&1 | grep DONE | tee -a $L )
  perf_wait ${arm}_$G 300
done; done
log "=== OVERNIGHT-3 DONE"
