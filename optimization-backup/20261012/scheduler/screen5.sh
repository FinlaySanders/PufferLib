#!/bin/bash
# Pass 5 (replay_sched4 binary, lazy + borrow): borrow-threshold scan — at 512 the 350 us arm idles ~24 us per cohort tick in waits too short to
# trigger a 30 us borrow; does a lower threshold convert that idle without over-borrowing? Plus pool repeats for spread.
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/screens5; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "SCREEN_START $(date -u +%FT%TZ) sched4=$(sha256sum $X/replay_sched4 | cut -c1-16)" >> $OUT/summary.txt
done_already(){ grep -q '^RESULT' $OUT/$1.log 2>/dev/null; }
pool(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env "$@" $X/replay_pool $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|env_wall_mean=[^ ]+|gpu_wait_mean=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
sched(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env SCHED_SEG=64 SCHED_GROUPFILL=0 SCHED_LAZY=1 "$@" $X/${BIN:-replay_sched4} $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'cold=[^ ]+|sps=[^ ]+|busy_sps=[^ ]+|busy_min=[^ ]+|busy_max=[^ ]+|idle_mean=[^ ]+|bar_mean=[^ ]+|steals=[^ ]+|migrations=[^ ]+|splits=[^ ]+|borrows=[^ ]+|live_cohorts=[^ ]+|own_P=[^ ]+|own_E=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
for N in 512 2048; do
 pool $N pool_f350 POOL_FWD_US=350
 pool $N pool_f800 POOL_FWD_US=800
 for B in 0 5 10 30 60; do
  sched $N l5m_c2_lazy_b$B  SCHED_C=2 SCHED_BORROW_US=$B SCHED_WIN_US=200 SCHED_FWD_US=350
  sched $N l15m_c2_lazy_b$B SCHED_C=2 SCHED_BORROW_US=$B SCHED_WIN_US=400 SCHED_FWD_US=800
 done
 sched $N l5m_c2_lazy_b5_w400 SCHED_C=2 SCHED_BORROW_US=5 SCHED_WIN_US=400 SCHED_FWD_US=350
 sched $N l5m_c1_lazy_b5      SCHED_C=1 SCHED_BORROW_US=5 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N l15m_c1_lazy_b5     SCHED_C=1 SCHED_BORROW_US=5 SCHED_WIN_US=400 SCHED_FWD_US=800
 for C in 1 2 4; do
  BIN=replay_sched5 sched $N l5m_c${C}_fit  SCHED_C=$C SCHED_BORROW_FIT=1 SCHED_WIN_US=200 SCHED_FWD_US=350
  BIN=replay_sched5 sched $N l15m_c${C}_fit SCHED_C=$C SCHED_BORROW_FIT=1 SCHED_WIN_US=400 SCHED_FWD_US=800
 done
 BIN=replay_sched5 sched $N fast_c2_fit SCHED_C=2 SCHED_BORROW_FIT=1 SCHED_WIN_US=100 SCHED_FWD_US=150
 pool $N pool_f150 POOL_FWD_US=150
 pool $N pool_f350_b POOL_FWD_US=350
done
echo "SCREEN_DONE $(date -u +%FT%TZ)" | tee -a $OUT/summary.txt
