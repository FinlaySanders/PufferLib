#!/bin/bash
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd /puffertank/experiments/nethack-engine-scaling-20261010 && LD_LIBRARY_PATH=/puffertank/experiments/nethack-compact-state-20261008/engines/rc2/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > /puffertank/experiments/nethack-rng-freedom-20261011/rc2_census_run.log 2>&1
grep -E 'RESULT|NH_CENSUS' /puffertank/experiments/nethack-rng-freedom-20261011/rc2_census_run.log | cut -c1-700
echo "CHAIN_RC2_DONE $(date -u +%T)"
