#!/bin/bash
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008; P=/puffertank/experiments/nethack-rng-freedom-20261011
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && LD_LIBRARY_PATH=$CS/engines/lz0/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > $P/lz0_replay.log 2>&1
grep -o 'seconds=[0-9.]* sps=[0-9.]* obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' $P/lz0_replay.log | sed 's/^/LZ0_REPLAY /'
cd $CS && nice -n 5 python3 check.py lz0 --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback" | sed 's/^/LZ0_GATE /'
echo "CHAIN_LZ0_DONE $(date -u +%T)"
