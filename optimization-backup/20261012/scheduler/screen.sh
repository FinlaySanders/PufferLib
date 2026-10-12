#!/bin/bash
# Scheduler screen: new cohort scheduler (replay_sched) vs today's trainer pool (replay_pool), 24 workers pinned one per physical
# core, engine tile_signed_pgo, fast protocol (warm 8192 decisions/game). Idempotent: arms whose log already holds a RESULT are skipped.
# Without SKIP_WAIT it waits for the champion campaign AND the s3002 rerun (nothing else may share the box while a seed runs).
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/screens; mkdir -p $OUT
RES=/puffertank/docker/champion10_20261011/fixed/RESULTS_FIXED.txt
[ -n "$SKIP_WAIT" ] || until grep -q RUN10_FIXED_DONE $RES 2>/dev/null && grep -q 'SEED 3002 (s3002_rerun)' $RES 2>/dev/null; do sleep 120; done
[ -n "$SKIP_WAIT" ] || while pgrep -f '^\S*/puffer (train|eval)' >/dev/null || pgrep -f '^/bin/bash \./rerun_seed' >/dev/null; do sleep 60; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "SCREEN_START $(date -u +%FT%TZ) engine=$(sha256sum $LD_LIBRARY_PATH/libnethack.so | cut -c1-16) sched=$(sha256sum $X/replay_sched | cut -c1-16)" >> $OUT/summary.txt
done_already(){ grep -q '^RESULT' $OUT/$1.log 2>/dev/null; }
pool(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env "$@" $X/replay_pool $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|env_wall_mean=[^ ]+|gpu_wait_mean=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
sched(){ local N=$1 tag=$2; shift 2; local steps=2048; [ $N -le 512 ] && steps=4096; done_already ${N}_$tag && return
 env SCHED_SEG=64 "$@" $X/replay_sched $N 24 8192 $steps $ACT > $OUT/${N}_$tag.log 2>&1
 echo "$N $tag $(grep -oE 'sps=[^ ]+|busy_sps=[^ ]+|busy_min=[^ ]+|busy_max=[^ ]+|idle_mean=[^ ]+|bar_mean=[^ ]+|steals=[^ ]+|migrations=[^ ]+|splits=[^ ]+|live_cohorts=[^ ]+|own_P=[^ ]+|own_E=[^ ]+|obs=[^ ]+' $OUT/${N}_$tag.log | tr '\n' ' ')" | tee -a $OUT/summary.txt; }
for N in 512 2048; do
 if [ $N -eq 512 ]; then G5="2,4 4,3 4,4 8,2 8,3"; G15="2,6 4,4 4,5 8,3 8,4"; V="4,3"; V15="4,5"; BIG=8; else G5="4,3 4,4 8,2 8,3 16,2"; G15="4,5 8,3 8,4 16,2 16,3"; V="8,3"; V15="8,4"; BIG=16; fi
 pool $N pool_f0   POOL_FWD_US=0
 pool $N pool_f350 POOL_FWD_US=350
 pool $N pool_f800 POOL_FWD_US=800
 [ $N -eq 2048 ] && pool $N pool4x512_f350 POOL_BUF=512 POOL_FWD_US=350
 sched $N bound_c4a1          SCHED_C=4 SCHED_A=1 SCHED_FWD_US=0
 sched $N bound_c4a1_static   SCHED_C=4 SCHED_A=1 SCHED_FWD_US=0 SCHED_STEAL=0
 sched $N bound_c${BIG}a1     SCHED_C=$BIG SCHED_A=1 SCHED_FWD_US=0
 for ca in $G5; do C=${ca%,*}; A=${ca#*,}; sched $N l5m_c${C}a${A} SCHED_C=$C SCHED_A=$A SCHED_WIN_US=200 SCHED_FWD_US=350; done
 C=${V%,*}; A=${V#*,}
 sched $N l5m_c${C}a${A}_static SCHED_C=$C SCHED_A=$A SCHED_WIN_US=200 SCHED_FWD_US=350 SCHED_STEAL=0
 sched $N l5m_c${C}a${A}_pw125  SCHED_C=$C SCHED_A=$A SCHED_WIN_US=200 SCHED_FWD_US=350 SCHED_PWEIGHT=1.25
 sched $N l5m_c${C}a${A}_s2     SCHED_C=$C SCHED_A=$A SCHED_WIN_US=200 SCHED_FWD_US=350 SCHED_STREAMS=2
 sched $N l5m_c${C}a${A}_nomig  SCHED_C=$C SCHED_A=$A SCHED_WIN_US=200 SCHED_FWD_US=350 SCHED_MIGRATE=0
 for ca in $G15; do C=${ca%,*}; A=${ca#*,}; sched $N l15m_c${C}a${A} SCHED_C=$C SCHED_A=$A SCHED_WIN_US=400 SCHED_FWD_US=800; done
 C=${V15%,*}; A=${V15#*,}
 sched $N l15m_c${C}a${A}_s2    SCHED_C=$C SCHED_A=$A SCHED_WIN_US=400 SCHED_FWD_US=800 SCHED_STREAMS=2
 pool $N pool_f350_b POOL_FWD_US=350
done
echo "SCREEN_DONE $(date -u +%FT%TZ)" | tee -a $OUT/summary.txt
