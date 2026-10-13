# shared helpers for the overnight queue
D=/puffertank/docker/perf_rot; X=/puffertank/experiments/nethack-scheduler-20261012; H=/puffertank/experiments/nethack-24h-20261009; L=$X/overnight/LOG.txt
log(){ echo "[$(date -u +%T)] $*" | tee -a $L; }
nreq=0
daemon_up(){ local t=$(cat $D/daemon_alive 2>/dev/null || echo 0); [ $(( $(date +%s) - t )) -lt 30 ]; }
wait_daemon(){ local t0=$(date +%s); while ! daemon_up && [ $(( $(date +%s)-t0 )) -lt ${1:-1200} ]; do sleep 10; done; daemon_up; }
perf_req(){ # perf_req <tag> <pattern> <mode> <events> <duration> <delay>  → writes a request; returns 1 if no daemon
  wait_daemon 60 || { log "PERF $1: daemon not running, skipped"; return 1; }
  nreq=$((nreq+1)); printf 'PATTERN=%s\nMODE=%s\nEVENTS=%s\nDURATION=%s\nDELAY=%s\n' "$2" "$3" "$4" "$5" "$6" > $D/requests/$(printf %03d $nreq)_$1.req; return 0; }
perf_wait(){ local t0=$(date +%s); while [ ! -f $D/results/$1.txt ] && [ $(( $(date +%s)-t0 )) -lt ${2:-300} ]; do sleep 5; done; [ -f $D/results/$1.txt ] && log "PERF $1: $(grep -oE '[0-9,]+\s+cpu_core/(cycles|instructions|branch-misses|L1-dcache-load-misses)/' $D/results/$1.txt | tr -s ' ' | tr '\n' ' ' | cut -c1-160)" || log "PERF $1: MISSING"; }
G1=cycles,instructions,L1-dcache-loads,L1-dcache-load-misses,L1-icache-load-misses,dTLB-load-misses,iTLB-load-misses,branch-instructions,branch-misses,LLC-loads,LLC-load-misses
G3=cycles,instructions,mem_load_retired.l1_miss,mem_load_retired.l2_miss,mem_load_retired.l3_miss,cycle_activity.stalls_total,cycle_activity.stalls_mem_any,cycle_activity.stalls_l1d_miss,br_misp_retired.all_branches,br_misp_retired.cond_taken,br_misp_retired.indirect,int_misc.clear_resteer_cycles,frontend_retired.l1i_miss
rot_run(){ # rot_run <A> <engine_build_dir> <tag> : one-core rotation run, 128 games, warm 4096, measure 16384 (~70-90 s)
  export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$2; local ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
  env SCHED_C=1 SCHED_A=$1 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $X/overnight/rot_$3.log 2>&1
  log "ROT $3 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $X/overnight/rot_$3.log | tr '\n' ' ')"; }
