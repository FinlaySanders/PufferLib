#!/bin/bash
# vision recalc cause census (CG build), after the packer A/B
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_vc.log
echo "stage VC start $(date -u +%T)" > $L
while ! grep -q STAGEP_DONE $P/stage_p.log; do sleep 15; done
cd $P && python3 apply_vis_census.py >> $L 2>&1
cmake --build $E/build_cg --target nethack -j8 > $E/build_cg_vc.log 2>&1; echo "cg build rc=$? errors=$(grep -c ' error' $E/build_cg_vc.log) $(date -u +%T)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_STATS=$P/mt2_vis_cause.txt SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $P/vc_run.log 2>&1
echo "census: $(grep -E 'vision_recalcs|vision_executed' $P/mt2_vis_cause.txt | tr '\n' ' ') steps=$((128*16384)) $(date -u +%T)" >> $L
echo "STAGEVC_DONE $(date -u +%T)" >> $L
