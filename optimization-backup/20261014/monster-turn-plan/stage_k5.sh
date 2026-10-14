#!/bin/bash
# v1.2 (S3 object search by box cells, S7 door-aware windows): apply, gates, same-binary A/B, corpus hash; PGO rebuild, PGO gates + A/B vs the
# landed engine. The live 1B seed is deferred to the final landing (user: focus on optimisations).
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008; N=/puffertank/experiments/nethack-engine-lines-20261014
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_k5.log
echo "stage K5 waiting for K4 $(date -u +%T)" > $L
while ! grep -q STAGEK4_DONE $P/stage_k4.log 2>/dev/null; do sleep 15; done
if grep -q nh_fidx $E/source/include/obj.h; then echo "v1.2 already applied" >> $L; else cd $P && python3 apply_mt2_v12.py >> $L 2>&1 || { echo "APPLY v1.2 FAILED" >> $L; echo "STAGEK5_DONE $(date -u +%T)" >> $L; exit 1; }; fi
for b in build build_trace build_cg; do cmake --build $E/$b --target nethack -j8 > $E/${b}_k5.log 2>&1; echo "$b rc=$? errors=$(grep -c ' error' $E/${b}_k5.log)" >> $L; done
grep -q "^build rc=0 errors=0" $L || { echo "BUILD FAILED" >> $L; grep -n ' error' $E/build_k5.log | head -5 >> $L; echo "STAGEK5_DONE $(date -u +%T)" >> $L; exit 1; }
cd $C && python3 check.py --quick lines_mt2 > $P/mt2_gates_k5.log 2>&1; echo "quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2_gates_k5.log) $(date -u +%T)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
run() { env LD_LIBRARY_PATH=$1 NH_MT2=$2 SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $3 2>&1; echo "NATIVE rot16 $4 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $3 | tr '\n' ' ') $(date -u +%T)" >> $L; }
for rep in 1 2; do for f in 0 1; do run $E/build $f $P/ab_k5_${f}_${rep}.log "v1.2 plain NH_MT2=$f rep$rep"; done; done
if ! grep -q "quick gates rc=0 passes=5" $L; then echo "GATES FAILED — stopping before hash/PGO" >> $L; echo "STAGEK5_DONE $(date -u +%T)" >> $L; exit 1; fi
cd $C && python3 check.py --hash-only lines_mt2 > $P/mt2_gates_full_k5.log 2>&1; echo "full hash rc=$? $(grep HASHES $P/mt2_gates_full_k5.log) $(date -u +%T)" >> $L
grep -q "full hash rc=0" $L || { echo "HASH FAILED — stopping" >> $L; echo "STAGEK5_DONE $(date -u +%T)" >> $L; exit 1; }
cd $N && python3 build_pgo.py mt2pgo > $N/mt2pgo_v12.build.out 2>&1; echo "pgo build rc=$? $(grep 'PGO READY' $N/mt2pgo_v12.build.out) $(date -u +%T)" >> $L
cd $C && python3 check.py --quick lines_mt2pgo > $P/mt2pgo_gates_k5.log 2>&1; echo "pgo quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2pgo_gates_k5.log) $(date -u +%T)" >> $L
for rep in 1 2; do run $N/engines/fastnle_ade/build 1 $P/ab_k5_ade_${rep}.log "PGO landed(fastnle_ade) rep$rep"; run $N/engines/mt2pgo/build 1 $P/ab_k5_pgo1_${rep}.log "PGO mt2 v1.2 NH_MT2=1 rep$rep"; done
echo "STAGEK5_DONE $(date -u +%T)" >> $L
