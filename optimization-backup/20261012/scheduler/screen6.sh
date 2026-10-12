#!/bin/bash
# Pass 6: segment length. At 512 the hybrid pays a latency-bound tail at every 64-tick barrier (all own cohorts aligned, nothing ready to borrow);
# the real barrier is the batch horizon (512 at the champion, 128 at 5M/2048). SEG scan with the knob-free rules (lazy + fit, C=1/2) and b30 reference.
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/screens6; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "SCREEN_START $(date -u +%FT%TZ) sched5=$(sha256sum $X/replay_sched5 | cut -c1-16)" >> $OUT/summary.txt
done_already(){ grep -q '^RESULT' $OUT/$1.log 2>/dev/null; }
pool(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env "$@" $X/replay_pool $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|env_wall_mean=[^ ]+|gpu_wait_mean=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
sched(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env SCHED_GROUPFILL=0 SCHED_LAZY=1 "$@" $X/replay_sched5 $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'cold=[^ ]+|sps=[^ ]+|busy_sps=[^ ]+|busy_min=[^ ]+|busy_max=[^ ]+|idle_mean=[^ ]+|bar_mean=[^ ]+|steals=[^ ]+|migrations=[^ ]+|splits=[^ ]+|borrows=[^ ]+|live_cohorts=[^ ]+|own_P=[^ ]+|own_E=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
N=512
pool $N pool_f350 POOL_FWD_US=350
pool $N pool_f800 POOL_FWD_US=800
for S in 64 512 4096; do
 sched $N l5m_c2_b30_seg$S  SCHED_SEG=$S SCHED_C=2 SCHED_BORROW_US=30 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N l15m_c2_b30_seg$S SCHED_SEG=$S SCHED_C=2 SCHED_BORROW_US=30 SCHED_WIN_US=400 SCHED_FWD_US=800
 sched $N l5m_c1_fit_seg$S  SCHED_SEG=$S SCHED_C=1 SCHED_BORROW_FIT=1 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N l15m_c1_fit_seg$S SCHED_SEG=$S SCHED_C=1 SCHED_BORROW_FIT=1 SCHED_WIN_US=400 SCHED_FWD_US=800
done
N=2048
pool $N pool_f350 POOL_FWD_US=350
pool $N pool_f800 POOL_FWD_US=800
for S in 128 2048; do
 sched $N l5m_c2_b30_seg$S  SCHED_SEG=$S SCHED_C=2 SCHED_BORROW_US=30 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N l15m_c2_b30_seg$S SCHED_SEG=$S SCHED_C=2 SCHED_BORROW_US=30 SCHED_WIN_US=400 SCHED_FWD_US=800
 sched $N l5m_c1_fit_seg$S  SCHED_SEG=$S SCHED_C=1 SCHED_BORROW_FIT=1 SCHED_WIN_US=200 SCHED_FWD_US=350
done
echo "SCREEN_DONE $(date -u +%FT%TZ)" | tee -a $OUT/summary.txt
