#!/bin/bash
# Trainer-level perf, pool vs scheduler: one plain pattern per arm (no regex alternation), waits up to 10 h for the host perf server.
source /puffertank/experiments/nethack-scheduler-20261012/overnight/lib.sh
L=$X/overnight/LOGC2.txt; log "=== PHASE C2: waiting for the host perf server"
wait_daemon 36000 || { log "daemon never came up"; exit 1; }
REC_EV='cycles:u,branch-misses:u,L1-icache-load-misses:u,L1-dcache-load-misses:u'
for arm in perf_pool perf_sched; do pat='binaries/sched_ctrl train'; [ $arm = perf_sched ] && pat='binaries/sched_v10 train'
  for G in G1 G3 REC; do ev=$G1; mode=stat; [ $G = G3 ] && ev=$G3; [ $G = REC ] && { mode=record; ev=$REC_EV; }
    perf_req ${arm}_$G "$pat" $mode "$ev" 50 25 || true
    ( cd $H && rm -rf runs/${arm}_$G && python3 campaign_ablate.py $X/overnight/ab_${arm}_$G.json 2>&1 | grep DONE | tee -a $L )
    perf_wait ${arm}_$G 240
  done; done
log "=== PHASE C2 DONE"
