#!/bin/bash
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; L=$P/stage_k17.log
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "stage K17 waiting for K16 $(date -u +%T)" > $L
while ! grep -q STAGEK16_DONE $P/stage_k16.log 2>/dev/null; do sleep 15; done
cd $P && python3 apply_mt2_visverify2.py >> $L 2>&1 || { echo "APPLY FAILED" >> $L; echo "STAGEK17_DONE" >> $L; exit 1; }
cmake --build $E/build_cg --target nethack -j8 > $E/build_cg_k17.log 2>&1; echo "cg build rc=$? errors=$(grep -c ' error' $E/build_cg_k17.log)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_STATS=$P/mt2_vis_verify2.txt SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 8 1 4096 16384 $ACT > /dev/null 2>&1; echo "8 games: $(grep vision_recalcs $P/mt2_vis_verify2.txt)" >> $L
echo "STAGEK17_DONE $(date -u +%T)" >> $L
