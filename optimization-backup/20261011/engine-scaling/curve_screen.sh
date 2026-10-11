#!/bin/bash
# Step-time vs games-per-core curve: same engine (mt7), 32 workers, games 256..4096 (unique streams replicated), fast protocol per size.
R=/puffertank/experiments/nethack-engine-scaling-20261010; E=/puffertank/experiments/nethack-compact-state-20261008/engines/mt7/build
ACTIONS=/puffertank/experiments/nethack-comprehensive-20261008/actions; OUT=$R/screens/curve; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$E
for g in 256 512 768 1024 1536 2048 3072 4096; do for rep in a b; do
  $R/harness_incpack/replay $g 32 8192 2048 $ACTIONS > $OUT/g${g}_$rep.log 2>&1
  echo "games=$g rep=$rep $(grep -o 'sps=[0-9.]*' $OUT/g${g}_$rep.log | tail -1) $(grep -o 'seconds=[0-9.]*' $OUT/g${g}_$rep.log | tail -1)"
done; done | tee $OUT/summary.txt
echo CURVE_DONE
