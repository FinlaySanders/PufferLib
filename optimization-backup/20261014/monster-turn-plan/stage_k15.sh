#!/bin/bash
# v1.3 (peaceful far monsters on the fast path, cached hero word): apply, build, 8-game hash check FIRST, quick gates, 128-game A/B, corpus hash
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_k15.log
echo "stage K15 waiting for K14 $(date -u +%T)" > $L
while ! grep -q STAGEK14_DONE $P/stage_k14.log 2>/dev/null; do sleep 15; done
if grep -q "nh_vis_fingerprint" $E/source/src/vision.c; then echo "v1.5 already applied" >> $L; else cd $P && python3 apply_mt2_v15_vision.py >> $L 2>&1 || { echo "APPLY v1.5 FAILED" >> $L; echo "STAGEK15_DONE $(date -u +%T)" >> $L; exit 1; }; fi
for b in build build_trace build_cg; do cmake --build $E/$b --target nethack -j8 > $E/${b}_k15.log 2>&1; echo "$b rc=$? errors=$(grep -c ' error' $E/${b}_k15.log)" >> $L; done
grep -q "^build rc=0 errors=0" $L || { echo "BUILD FAILED" >> $L; grep -n ' error' $E/build_k15.log | head -5 >> $L; echo "STAGEK15_DONE $(date -u +%T)" >> $L; exit 1; }
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
h8() { env LD_LIBRARY_PATH=$E/build NH_MT2=$1 SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 8 1 4096 16384 $ACT 2>&1 | grep -oE 'obs=[^ ]+'; }
H0=$(h8 0); H1=$(h8 1); echo "8-game hash off=$H0 on=$H1 $(date -u +%T)" >> $L
[ "$H0" = "$H1" ] || { echo "8-GAME HASH MISMATCH — stopping" >> $L; echo "STAGEK15_DONE $(date -u +%T)" >> $L; exit 1; }
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_STATS=$P/mt2_vis_verify.txt SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > /dev/null 2>&1; echo "vision verify (128 games): $(grep vision_recalcs $P/mt2_vis_verify.txt) $(date -u +%T)" >> $L
grep -q "VIOLATIONS 0 " $P/mt2_vis_verify.txt || { echo "VISION SKIP VIOLATIONS — stopping" >> $L; echo "STAGEK15_DONE $(date -u +%T)" >> $L; exit 1; }
cd $C && python3 check.py --quick lines_mt2 > $P/mt2_gates_k15.log 2>&1; echo "quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2_gates_k15.log) $(date -u +%T)" >> $L
run() { env LD_LIBRARY_PATH=$1 NH_MT2=$2 SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $3 2>&1; echo "NATIVE rot16 $4 $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $3 | tr '\n' ' ') $(date -u +%T)" >> $L; }
for rep in 1 2; do for f in 0 1; do run $E/build $f $P/ab_k15_${f}_${rep}.log "v1.5 plain NH_MT2=$f rep$rep"; done; done
cd $C && python3 check.py --hash-only lines_mt2 > $P/mt2_gates_full_k15.log 2>&1; echo "full hash rc=$? $(grep HASHES $P/mt2_gates_full_k15.log) $(date -u +%T)" >> $L
echo "STAGEK15_DONE $(date -u +%T)" >> $L
