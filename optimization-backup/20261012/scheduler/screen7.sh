#!/bin/bash
# Pass 7: window = forward size. (a) window equal to the forward (one stream keeps up; forwards = today's size): W350/F350, W800/F800.
# (b) the 11-Oct GPU lever "fewer, bigger forwards" via a long window: W1400/F330 at 2048 gives ~512-row forwards (4x fewer launches, PPO 0.98->0.93 s
# measured then) while each core's active set stays small — the rollout side of that trade, measured here. 2048 games, knob-free design (C1, lazy, borrow).
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/screens7; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "SCREEN_START $(date -u +%FT%TZ) sched5=$(sha256sum $X/replay_sched5 | cut -c1-16)" >> $OUT/summary.txt
done_already(){ grep -q '^RESULT' $OUT/$1.log 2>/dev/null; }
pool(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env "$@" $X/replay_pool $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|env_wall_mean=[^ ]+|gpu_wait_mean=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
sched(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env SCHED_GROUPFILL=0 SCHED_LAZY=1 SCHED_C=1 SCHED_BORROW_US=0 "$@" $X/replay_sched5 $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'cold=[^ ]+|sps=[^ ]+|busy_sps=[^ ]+|busy_min=[^ ]+|busy_max=[^ ]+|idle_mean=[^ ]+|bar_mean=[^ ]+|steals=[^ ]+|migrations=[^ ]+|splits=[^ ]+|borrows=[^ ]+|live_cohorts=[^ ]+|own_P=[^ ]+|own_E=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
N=2048; SEG=${SEG7:-128}
pool $N pool_f350 POOL_FWD_US=350
pool $N pool_f800 POOL_FWD_US=800
pool $N pool4x512_f330 POOL_BUF=512 POOL_FWD_US=330
sched $N w350_f350_seg$SEG   SCHED_SEG=$SEG SCHED_WIN_US=350 SCHED_FWD_US=350
sched $N w800_f800_seg$SEG   SCHED_SEG=$SEG SCHED_WIN_US=800 SCHED_FWD_US=800
sched $N w1400_f330_seg$SEG  SCHED_SEG=$SEG SCHED_WIN_US=1400 SCHED_FWD_US=330
sched $N w1400_f330_s1_seg$SEG SCHED_SEG=$SEG SCHED_WIN_US=1400 SCHED_FWD_US=330 SCHED_STREAMS=1
sched $N w700_f330_seg$SEG   SCHED_SEG=$SEG SCHED_WIN_US=700 SCHED_FWD_US=330
sched $N w200_f350_seg$SEG   SCHED_SEG=$SEG SCHED_WIN_US=200 SCHED_FWD_US=350
pool $N pool_f350_b POOL_FWD_US=350
echo "SCREEN_DONE $(date -u +%FT%TZ)" | tee -a $OUT/summary.txt
