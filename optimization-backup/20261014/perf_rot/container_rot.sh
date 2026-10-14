#!/bin/bash
# Container side: after the scheduler A/B finishes, run rotation 1/4/16/64 on one pinned P-core (cpu 2): 128 games, warm 4096, measure 16384 ticks (~70 s each).
X=/puffertank/experiments/nethack-scheduler-20261012; D=/puffertank/docker/perf_rot
while ! grep -q AB_DONE $X/trainer/ab_rep.launcher.log 2>/dev/null; do sleep 10; done; sleep 5
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
for A in 1 4 16 64; do
  echo "[$(date -u +%T)] rotation A=$A starting" | tee -a $D/container_rot.log
  env SCHED_C=1 SCHED_A=$A SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $D/rot$A.log 2>&1
  echo "[$(date -u +%T)] A=$A $(grep -oE ' sps=[^ ]+|busy_sps=[^ ]+|obs=[^ ]+' $D/rot$A.log | tr '\n' ' ')" | tee -a $D/container_rot.log
done
echo CONTAINER_ROT_DONE | tee -a $D/container_rot.log
