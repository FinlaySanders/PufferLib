#!/bin/bash
# Stage 1 matrix: cohort scheduler policies vs today's interleaving, 2048 games, 32 workers, fast protocol. Hash must stay b97835c62aaf388f.
R=/puffertank/experiments/nethack-engine-scaling-20261010; E=/puffertank/experiments/nethack-compact-state-20261008/engines/mt7/build
ACTIONS=/puffertank/experiments/nethack-comprehensive-20261008/actions; OUT=$R/screens/cohort; mkdir -p $OUT
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
while ! grep -q CURVE_DONE $S/curve.log; do sleep 20; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0 LD_LIBRARY_PATH=$E
run() { local tag=$1; shift; env "$@" $R/harness_cohort/replay_cohort 2048 32 8192 2048 $ACTIONS > $OUT/$tag.log 2>&1; echo "$tag $(grep -o 'sps=[0-9.]* busy_sps=[0-9.]* busy_mean=[0-9.]* busy_max=[0-9.]* idle_mean=[0-9.]* obs=[0-9a-f]*' $OUT/$tag.log)"; }
$R/harness_incpack/replay 2048 32 8192 2048 $ACTIONS > $OUT/baseline.log 2>&1; echo "baseline $(grep -o 'sps=[0-9.]*' $OUT/baseline.log) $(grep -o 'obs=[0-9a-f]*' $OUT/baseline.log)"
run A4_lat0 COHORT_A=4 COHORT_LAT_US=0
run A1_lat0 COHORT_A=1 COHORT_LAT_US=0
run A1_lat300 COHORT_A=1 COHORT_LAT_US=300
run A1_lat600 COHORT_A=1 COHORT_LAT_US=600
run A1_lat1000 COHORT_A=1 COHORT_LAT_US=1000
run A2_lat300 COHORT_A=2 COHORT_LAT_US=300
run A2_lat600 COHORT_A=2 COHORT_LAT_US=600
run A2_lat1000 COHORT_A=2 COHORT_LAT_US=1000
run A4_lat0_pin COHORT_A=4 COHORT_LAT_US=0 COHORT_PIN=1
run A1_lat0_pin COHORT_A=1 COHORT_LAT_US=0 COHORT_PIN=1
run A1_lat600_pin COHORT_A=1 COHORT_LAT_US=600 COHORT_PIN=1
run A2_lat600_pin COHORT_A=2 COHORT_LAT_US=600 COHORT_PIN=1
$R/harness_incpack/replay 2048 32 8192 2048 $ACTIONS > $OUT/baseline_b.log 2>&1; echo "baseline_b $(grep -o 'sps=[0-9.]*' $OUT/baseline_b.log)"
echo COHORT_DONE
