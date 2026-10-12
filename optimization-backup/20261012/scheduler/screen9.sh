#!/bin/bash
# Pass 9: population scaling 2048 / 4096 / 8192 — pool vs the final hybrid (C1 lazy borrow event, seg128, window = forward 350). Measured 2048 ticks after warm 8192.
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/screens9; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "SCREEN_START $(date -u +%FT%TZ) sched6=$(sha256sum $X/replay_sched6 | cut -c1-16)" >> $OUT/summary.txt
done_already(){ grep -q '^RESULT' $OUT/$1.log 2>/dev/null; }
pool(){ local N=$1 tag=$2; shift 2; done_already ${N}_$tag && return
 env "$@" $X/replay_pool $N 24 8192 2048 $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|env_wall_mean=[^ ]+|gpu_wait_mean=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
sched(){ local N=$1 tag=$2; shift 2; done_already ${N}_$tag && return
 env SCHED_GROUPFILL=0 SCHED_LAZY=1 SCHED_C=1 SCHED_BORROW_US=0 SCHED_EVENT=1 SCHED_SEG=128 "$@" $X/replay_sched6 $N 24 8192 2048 $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'cold=[^ ]+|sps=[^ ]+|busy_sps=[^ ]+|busy_min=[^ ]+|busy_max=[^ ]+|idle_mean=[^ ]+|bar_mean=[^ ]+|steals=[^ ]+|migrations=[^ ]+|splits=[^ ]+|borrows=[^ ]+|live_cohorts=[^ ]+|own_P=[^ ]+|own_E=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
for N in 4096 8192; do
 pool $N pool_f350 POOL_FWD_US=350
 sched $N w350_f350 SCHED_WIN_US=350 SCHED_FWD_US=350
 sched $N bound_f0 SCHED_WIN_US=0 SCHED_FWD_US=0
 sched $N w800_f800 SCHED_WIN_US=800 SCHED_FWD_US=800
 pool $N pool_f800 POOL_FWD_US=800
done
echo "SCREEN_DONE $(date -u +%FT%TZ)" | tee -a $OUT/summary.txt
