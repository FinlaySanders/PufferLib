#!/bin/bash
# Pass 8 (replay_sched6): event-driven readiness + spin-wait borrowing (SCHED_EVENT=1) vs the sleeping/scanning version — does it remove the
# 512-game short-latency deficiency? Window = forward (today's GPU traffic) plus the W200 case; champion horizon seg512 at 512, seg128 at 2048.
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/screens8; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "SCREEN_START $(date -u +%FT%TZ) sched6=$(sha256sum $X/replay_sched6 | cut -c1-16)" >> $OUT/summary.txt
done_already(){ grep -q '^RESULT' $OUT/$1.log 2>/dev/null; }
pool(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env "$@" $X/replay_pool $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|env_wall_mean=[^ ]+|gpu_wait_mean=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
sched(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env SCHED_GROUPFILL=0 SCHED_LAZY=1 SCHED_C=1 SCHED_BORROW_US=0 "$@" $X/replay_sched6 $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'cold=[^ ]+|sps=[^ ]+|busy_sps=[^ ]+|busy_min=[^ ]+|busy_max=[^ ]+|idle_mean=[^ ]+|bar_mean=[^ ]+|steals=[^ ]+|migrations=[^ ]+|splits=[^ ]+|borrows=[^ ]+|live_cohorts=[^ ]+|own_P=[^ ]+|own_E=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
N=512
pool $N pool_f350 POOL_FWD_US=350
pool $N pool_f800 POOL_FWD_US=800
for E in 0 1; do
 sched $N w350_f350_ev$E SCHED_EVENT=$E SCHED_SEG=512 SCHED_WIN_US=350 SCHED_FWD_US=350
 sched $N w200_f350_ev$E SCHED_EVENT=$E SCHED_SEG=512 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N w800_f800_ev$E SCHED_EVENT=$E SCHED_SEG=512 SCHED_WIN_US=800 SCHED_FWD_US=800
done
sched $N w350_f350_ev1_fit SCHED_EVENT=1 SCHED_BORROW_FIT=1 SCHED_SEG=512 SCHED_WIN_US=350 SCHED_FWD_US=350
sched $N w350_f350_ev1_c2 SCHED_EVENT=1 SCHED_C=2 SCHED_SEG=512 SCHED_WIN_US=350 SCHED_FWD_US=350
N=2048
pool $N pool_f350 POOL_FWD_US=350
pool $N pool_f800 POOL_FWD_US=800
for E in 0 1; do
 sched $N w350_f350_ev$E SCHED_EVENT=$E SCHED_SEG=128 SCHED_WIN_US=350 SCHED_FWD_US=350
 sched $N w800_f800_ev$E SCHED_EVENT=$E SCHED_SEG=128 SCHED_WIN_US=800 SCHED_FWD_US=800
done
echo "SCREEN_DONE $(date -u +%FT%TZ)" | tee -a $OUT/summary.txt
