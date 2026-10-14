#!/bin/bash
# Line-level profile run: rotation 16 on one pinned P-core, 256 games (2x work, ~130 s) so the host perf record window lands inside the run.
X=/puffertank/experiments/nethack-scheduler-20261012; D=/puffertank/docker/perf_rot
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
env SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 256 1 4096 16384 $ACT > $D/annot_rot16b.log 2>&1
echo ANNOT_ROT16B_DONE >> $D/annot_rot16b.log
