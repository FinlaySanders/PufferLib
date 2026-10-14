#!/bin/bash
# v1.1: rebuild, gates, same-binary A/B, full hash; then PGO build and the landing-style A/B against the landed PGO engine
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008; N=/puffertank/experiments/nethack-engine-lines-20261014
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_k4.log
echo "stage K4 waiting for K3 $(date -u +%T)" > $L
while ! grep -q STAGEK3_DONE $P/stage_k3.log 2>/dev/null; do sleep 15; done
for b in build build_trace build_cg; do cmake --build $E/$b --target nethack -j8 > $E/${b}_k4.log 2>&1; echo "$b rc=$? errors=$(grep -c ' error' $E/${b}_k4.log)" >> $L; done
cd $C && python3 check.py --quick lines_mt2 > $P/mt2_gates_k4.log 2>&1; echo "quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2_gates_k4.log) $(date -u +%T)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
run() { env LD_LIBRARY_PATH=$1 NH_MT2=$2 SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $3 2>&1; echo "NATIVE rot16 $4 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $3 | tr '\n' ' ') $(date -u +%T)" >> $L; }
for rep in 1 2; do for f in 0 1; do run $E/build $f $P/ab_k4_${f}_${rep}.log "v1.1 plain NH_MT2=$f rep$rep"; done; done
if grep -q "quick gates rc=0" $L; then cd $C && python3 check.py --hash-only lines_mt2 > $P/mt2_gates_full_k4.log 2>&1; echo "full hash rc=$? $(grep HASHES $P/mt2_gates_full_k4.log) $(date -u +%T)" >> $L; fi
cd $N && python3 build_pgo.py mt2pgo > $N/mt2pgo.build.out 2>&1; echo "pgo build rc=$? $(grep 'PGO READY' $N/mt2pgo.build.out) $(date -u +%T)" >> $L
ln -sfn $N/engines/mt2pgo $C/engines/lines_mt2pgo
for rep in 1 2; do run $N/engines/fastnle_ade/build 1 $P/ab_k4_ade_${rep}.log "PGO landed(fastnle_ade) rep$rep"; run $N/engines/mt2pgo/build 0 $P/ab_k4_pgo0_${rep}.log "PGO mt2 NH_MT2=0 rep$rep"; run $N/engines/mt2pgo/build 1 $P/ab_k4_pgo1_${rep}.log "PGO mt2 NH_MT2=1 rep$rep"; done
cd $C && python3 check.py --quick lines_mt2pgo > $P/mt2pgo_gates.log 2>&1; echo "pgo quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2pgo_gates.log) $(date -u +%T)" >> $L
echo "STAGEK4_DONE $(date -u +%T)" >> $L
