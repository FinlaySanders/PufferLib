#!/bin/bash
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; L=$P/stage_k18.log
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "stage K18 waiting for K17 $(date -u +%T)" > $L
while ! grep -q STAGEK17_DONE $P/stage_k17.log 2>/dev/null; do sleep 15; done
cd $P && python3 apply_mt2_visverify3.py >> $L 2>&1 || { echo "APPLY FAILED" >> $L; echo "STAGEK18_DONE" >> $L; exit 1; }
cmake --build $E/build_cg --target nethack -j8 > $E/build_cg_k18.log 2>&1; echo "cg build rc=$? errors=$(grep -c ' error' $E/build_cg_k18.log)" >> $L
grep -n ' error' $E/build_cg_k18.log | head -3 >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_STATS=$P/mt2_vis_verify3.txt SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 8 1 4096 16384 $ACT 2>&1 | grep -oE 'obs=[^ ]+' >> $L; echo "8 games: $(grep -E 'vision_recalcs|oracle' $P/mt2_vis_verify3.txt | tr '\n' ' ')" >> $L
echo "STAGEK18_DONE $(date -u +%T)" >> $L
