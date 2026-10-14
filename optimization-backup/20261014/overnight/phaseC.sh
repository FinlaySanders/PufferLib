#!/bin/bash
source /puffertank/experiments/nethack-scheduler-20261012/overnight/lib.sh
L=$X/overnight/LOGC.txt; log "=== PHASE C rerun: trainer perf pool vs scheduler"
TPAT='/binaries/sched_(ctrl|v10) train'; REC_EV='cycles:u,branch-misses:u,L1-icache-load-misses:u,L1-dcache-load-misses:u'
wait_daemon 300 || { log "daemon down"; exit 1; }
for arm in perf_pool perf_sched; do for G in G1 G3 REC; do
  ev=$G1; mode=stat; [ $G = G3 ] && ev=$G3; [ $G = REC ] && { mode=record; ev=$REC_EV; }
  perf_req ${arm}_$G "$TPAT" $mode "$ev" 50 25 || true
  ( cd $H && rm -rf runs/${arm}_$G && python3 campaign_ablate.py $X/overnight/ab_${arm}_$G.json 2>&1 | grep DONE | tee -a $L )
  perf_wait ${arm}_$G 240
done; done
log "=== PHASE C DONE"
