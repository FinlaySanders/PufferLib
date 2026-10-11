#!/bin/bash
# Prefetch-mode screen on identical binaries: ./pf_screen.sh <games> <label> mode...
R=/puffertank/experiments/nethack-engine-scaling-20261010; E=/puffertank/experiments/nethack-compact-state-20261008/engines/heat1pf/build
ACTIONS=/puffertank/experiments/nethack-comprehensive-20261008/actions; GAMES=$1; LABEL=$2; shift 2
OUT=$R/screens/$LABEL; mkdir -p $OUT
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$E
for m in "$@"; do
  CPU_PREFETCH=$m $R/harness_pf/replay $GAMES 32 8192 2048 $ACTIONS > $OUT/mode${m}_$GAMES.log 2>&1
  echo "mode=$m games=$GAMES $(grep -o 'sps=[0-9.]*' $OUT/mode${m}_$GAMES.log | tail -1) $(grep -o 'obs=[0-9a-f]*' $OUT/mode${m}_$GAMES.log | tail -1)"
done | tee -a $OUT/summary.txt
