#!/bin/bash
# Step 1: callgrind cache footprint of the retained engine, 512 games, two last-level-cache shares.
R=/puffertank/experiments/nethack-engine-scaling-20261010
H=/puffertank/experiments/nethack-compact-state-20261008
ENGINE=$H/engines/movement_object_presence_pgo_followthrough/build
ACTIONS=/puffertank/experiments/nethack-comprehensive-20261008/actions
export LD_LIBRARY_PATH=$ENGINE NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R
VG="nice -n 19 valgrind --tool=callgrind --cache-sim=yes --instr-atstart=no --D1=49152,12,64"
echo "SMOKE $(date -u +%T)"
$VG --LL=37748736,18,64 --callgrind-out-file=$R/callgrind.smoke.out $H/replay 512 0 2 1 $ACTIONS > $R/replay.smoke.log 2>&1 || { echo "SMOKE FAILED rc=$?"; tail -20 $R/replay.smoke.log; exit 1; }
grep -E "RESULT|sps" $R/replay.smoke.log | tail -2
for arm in "share512:37748736,18,64" "share2048:9437184,9,64"; do
  name=${arm%%:*}; ll=${arm##*:}
  echo "START $name LL=$ll $(date -u +%T)"
  $VG --LL=$ll --callgrind-out-file=$R/callgrind.$name.out $H/replay 512 0 4096 128 $ACTIONS > $R/replay.$name.log 2>&1 || echo "FAILED $name rc=$?"
  grep -E "RESULT" $R/replay.$name.log | tail -1 | cut -c1-200
  echo "DONE $name $(date -u +%T)"
done
python3 $R/footprint_report.py > $R/FOOTPRINT.md 2> $R/footprint_report.err
echo FOOTPRINT_DONE
