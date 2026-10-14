#!/bin/bash
# Trainer-level perf: match each trainer by its unique run directory in argv ('runs/<label>/'), one request at a time with an idle server.
source /puffertank/experiments/nethack-scheduler-20261012/overnight/lib.sh
L=$X/overnight/LOGC4.txt; log "=== PHASE C4"
REC_EV='cycles:u,branch-misses:u,L1-icache-load-misses:u,L1-dcache-load-misses:u'
for arm in perf_pool perf_sched; do for G in G1 G3; do
  ev=$G1; mode=stat; [ $G = G3 ] && ev=$G3; [ $G = REC ] && { mode=record; ev=$REC_EV; }
  t0=$(date +%s); while ! daemon_up && [ $(( $(date +%s)-t0 )) -lt 900 ]; do sleep 5; done
  perf_req ${arm}_$G "runs/${arm}_$G/" $mode "$ev" 50 25 || true
  ( cd $H && rm -rf runs/${arm}_$G && python3 campaign_ablate.py $X/overnight/ab_${arm}_$G.json 2>&1 | grep DONE | tee -a $L )
  perf_wait ${arm}_$G 400
done; done
log "=== PHASE C4 DONE"
