#!/bin/bash
# I-cache vs D-cache attribution of the 1-game -> 4-game rotation step: callgrind cache sim, 1 worker, 32 games, warm 512, measure 256 ticks.
# rot1 = C1 A1 F0 (each game stepped to completion: L1-warm bound); rot4 = C1 A4 fixed F0 (4 games in rotation); rot16 = A16.
X=/puffertank/experiments/nethack-scheduler-20261012; OUT=$X/icache; cd $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
export LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
for A in 1 4 16; do
 env SCHED_C=1 SCHED_A=$A SCHED_GROUPFILL=1 SCHED_SEG=256 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 \
  valgrind --tool=callgrind --cache-sim=yes --I1=49152,12,64 --D1=49152,12,64 --LL=2097152,16,64 --collect-atstart=yes \
  --callgrind-out-file=$OUT/cg_rot$A.out $X/replay_sched6 32 1 512 256 $ACT > $OUT/rot$A.log 2>&1
 echo "rot$A $(grep -oE 'sps=[^ ]+|obs=[^ ]+' $OUT/rot$A.log | tr '\n' ' ') $(grep -E '^(summary|totals):' $OUT/cg_rot$A.out | head -1)"
done
echo ICACHE_DONE
