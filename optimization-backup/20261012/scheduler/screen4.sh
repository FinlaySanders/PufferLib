#!/bin/bash
# Pass 4 (replay_sched4): group-synchronous refill (no mid-segment stragglers) x borrow-when-idle, fixed A. Realistic latencies.
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/screens4; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "SCREEN_START $(date -u +%FT%TZ) sched4=$(sha256sum $X/replay_sched4 | cut -c1-16)" >> $OUT/summary.txt
done_already(){ grep -q '^RESULT' $OUT/$1.log 2>/dev/null; }
pool(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env "$@" $X/replay_pool $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|env_wall_mean=[^ ]+|gpu_wait_mean=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
sched(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env SCHED_SEG=64 SCHED_GROUPFILL=1 "$@" $X/replay_sched4 $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|busy_sps=[^ ]+|busy_min=[^ ]+|busy_max=[^ ]+|idle_mean=[^ ]+|bar_mean=[^ ]+|steals=[^ ]+|migrations=[^ ]+|splits=[^ ]+|borrows=[^ ]+|live_cohorts=[^ ]+|own_P=[^ ]+|own_E=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
for N in 512 2048; do
 pool $N pool_f350 POOL_FWD_US=350
 pool $N pool_f800 POOL_FWD_US=800
 pool $N pool_f150 POOL_FWD_US=150
 # exact repeats of the pass-3 winners (no group refill)
 for C in 2 4; do
  sched $N l5m_c${C}_lazy_b30  SCHED_GROUPFILL=0 SCHED_C=$C SCHED_LAZY=1 SCHED_BORROW_US=30 SCHED_WIN_US=200 SCHED_FWD_US=350
  sched $N l15m_c${C}_lazy_b30 SCHED_GROUPFILL=0 SCHED_C=$C SCHED_LAZY=1 SCHED_BORROW_US=30 SCHED_WIN_US=400 SCHED_FWD_US=800
 done
 # group-synchronous refill, fixed in-flight count, reluctant borrowing
 for ca in 1,2 1,4 2,2 2,3 2,4 4,2 4,3; do C=${ca%,*}; A=${ca#*,}
  sched $N l5m_c${C}a${A}_gf_b30  SCHED_C=$C SCHED_A=$A SCHED_WIN_US=200 SCHED_FWD_US=350 SCHED_BORROW_US=30
  sched $N l15m_c${C}a${A}_gf_b30 SCHED_C=$C SCHED_A=$A SCHED_WIN_US=400 SCHED_FWD_US=800 SCHED_BORROW_US=30
 done
 sched $N l5m_c4a3_gf      SCHED_C=4 SCHED_A=3 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N fast_c4a2_gf_b30 SCHED_C=4 SCHED_A=2 SCHED_WIN_US=100 SCHED_FWD_US=150 SCHED_BORROW_US=30
 sched $N fast_c2_lazy_b30 SCHED_GROUPFILL=0 SCHED_C=2 SCHED_LAZY=1 SCHED_BORROW_US=30 SCHED_WIN_US=100 SCHED_FWD_US=150
 pool $N pool_f350_b POOL_FWD_US=350
done
echo "SCREEN_DONE $(date -u +%FT%TZ)" | tee -a $OUT/summary.txt
