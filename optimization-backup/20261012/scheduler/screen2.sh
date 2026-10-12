#!/bin/bash
# Pass 2 (replay_sched2): timer slack 1 us + spin for short waits, lazy hot-set growth, per-window forwards on STREAMS. Realistic latencies only.
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/screens2; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "SCREEN_START $(date -u +%FT%TZ) sched2=$(sha256sum $X/replay_sched2 | cut -c1-16)" >> $OUT/summary.txt
done_already(){ grep -q '^RESULT' $OUT/$1.log 2>/dev/null; }
pool(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env "$@" $X/replay_pool $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|env_wall_mean=[^ ]+|gpu_wait_mean=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
sched(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env SCHED_SEG=64 "$@" $X/replay_sched2 $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|busy_sps=[^ ]+|busy_min=[^ ]+|busy_max=[^ ]+|idle_mean=[^ ]+|bar_mean=[^ ]+|steals=[^ ]+|migrations=[^ ]+|splits=[^ ]+|live_cohorts=[^ ]+|own_P=[^ ]+|own_E=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
for N in 512 2048; do
 pool $N pool_f350 POOL_FWD_US=350
 pool $N pool_f800 POOL_FWD_US=800
 for C in 2 4 8; do sched $N l5m_c${C}_lazy SCHED_C=$C SCHED_LAZY=1 SCHED_WIN_US=200 SCHED_FWD_US=350; done
 sched $N l5m_c4a3  SCHED_C=4 SCHED_A=3 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N l5m_c4a4  SCHED_C=4 SCHED_A=4 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N l5m_c8a3  SCHED_C=8 SCHED_A=3 SCHED_WIN_US=200 SCHED_FWD_US=350
 sched $N l5m_c4_lazy_s1 SCHED_C=4 SCHED_LAZY=1 SCHED_WIN_US=200 SCHED_FWD_US=350 SCHED_STREAMS=1
 sched $N l5m_c4_lazy_s2 SCHED_C=4 SCHED_LAZY=1 SCHED_WIN_US=200 SCHED_FWD_US=350 SCHED_STREAMS=2
 sched $N l5m_c4_lazy_w100 SCHED_C=4 SCHED_LAZY=1 SCHED_WIN_US=100 SCHED_FWD_US=350
 for C in 4 8; do sched $N l15m_c${C}_lazy SCHED_C=$C SCHED_LAZY=1 SCHED_WIN_US=400 SCHED_FWD_US=800; done
 sched $N l15m_c8a4 SCHED_C=8 SCHED_A=4 SCHED_WIN_US=400 SCHED_FWD_US=800
 sched $N l15m_c8_lazy_s2 SCHED_C=8 SCHED_LAZY=1 SCHED_WIN_US=400 SCHED_FWD_US=800 SCHED_STREAMS=2
 sched $N fast_c4_lazy SCHED_C=4 SCHED_LAZY=1 SCHED_WIN_US=100 SCHED_FWD_US=150
 sched $N bound_c4a1 SCHED_C=4 SCHED_A=1 SCHED_FWD_US=0
done
echo "SCREEN_DONE $(date -u +%FT%TZ)" | tee -a $OUT/summary.txt
