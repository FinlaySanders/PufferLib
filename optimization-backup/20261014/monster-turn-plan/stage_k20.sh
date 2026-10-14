#!/bin/bash
# v1.5b (vision exact skip, oracle-clean): builds, 8-game hash, quick gates, 128-game A/B, corpus hash; then the v1.6 near-kernel chain
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_k20.log
echo "stage K20 start $(date -u +%T)" > $L
for b in build build_trace; do cmake --build $E/$b --target nethack -j8 > $E/${b}_k20.log 2>&1; echo "$b rc=$? errors=$(grep -c ' error' $E/${b}_k20.log)" >> $L; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
h8() { env LD_LIBRARY_PATH=$E/build NH_MT2=$1 SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 8 1 4096 16384 $ACT 2>&1 | grep -oE 'obs=[^ ]+'; }
H0=$(h8 0); H1=$(h8 1); echo "8-game hash off=$H0 on=$H1 (old-path reference obs=948bc4a0d1ab2b7b) $(date -u +%T)" >> $L
[ "$H1" = "obs=948bc4a0d1ab2b7b" ] || { echo "8-GAME HASH MISMATCH — stopping" >> $L; echo "STAGEK20_DONE $(date -u +%T)" >> $L; exit 1; }
cd $C && python3 check.py --quick lines_mt2 > $P/mt2_gates_k20.log 2>&1; echo "quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2_gates_k20.log) $(date -u +%T)" >> $L
run() { env LD_LIBRARY_PATH=$1 NH_MT2=$2 SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $3 2>&1; echo "NATIVE rot16 $4 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $3 | tr '\n' ' ') $(date -u +%T)" >> $L; }
for rep in 1 2; do for f in 0 1; do run $E/build $f $P/ab_k20_${f}_${rep}.log "v1.5b plain NH_MT2=$f rep$rep"; done; done
cd $C && python3 check.py --hash-only lines_mt2 > $P/mt2_gates_full_k20.log 2>&1; echo "full hash rc=$? $(grep HASHES $P/mt2_gates_full_k20.log) $(date -u +%T)" >> $L
echo "STAGEK20_DONE $(date -u +%T)" >> $L
grep -q "full hash rc=0" $L && bash $P/stage_k19.sh
