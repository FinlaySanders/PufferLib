#!/bin/bash
# Wait for the host perf server to go idle (fresh heartbeat), then run the trainer-level perf pairs with the server free: request, trainer, measure.
source /puffertank/experiments/nethack-scheduler-20261012/overnight/lib.sh
L=$X/overnight/LOGC3.txt; log "=== PHASE C3: waiting for an idle server"
t0=$(date +%s); while ! daemon_up && [ $(( $(date +%s)-t0 )) -lt 1500 ]; do sleep 5; done
daemon_up || { log "server not idle after 25 min; stop"; exit 1; }
REC_EV='cycles:u,branch-misses:u,L1-icache-load-misses:u,L1-dcache-load-misses:u'
for arm in perf_pool perf_sched; do pat='binaries/sched_ctrl train'; [ $arm = perf_sched ] && pat='binaries/sched_v10 train'
  for G in G1 G3 REC; do ev=$G1; mode=stat; [ $G = G3 ] && ev=$G3; [ $G = REC ] && { mode=record; ev=$REC_EV; }
    t0=$(date +%s); while ! daemon_up && [ $(( $(date +%s)-t0 )) -lt 900 ]; do sleep 5; done
    perf_req ${arm}_$G "$pat" $mode "$ev" 50 25 || true
    ( cd $H && rm -rf runs/${arm}_$G && python3 campaign_ablate.py $X/overnight/ab_${arm}_$G.json 2>&1 | grep DONE | tee -a $L )
    perf_wait ${arm}_$G 400
  done; done
log "=== PHASE C3 DONE"
