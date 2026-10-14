#!/bin/bash
# after v1.2: (a) whole-step callgrind with the kernel on (mature 8 games) to re-rank the remaining buckets; (b) eligible-only profile of v1.2;
# (c) event census of v1.2 fallbacks (NH_MT2=0 counters are the old path; run with the kernel on via the plain build's counters is not available,
#     so the census uses the CG build with NH_MT2=0 to keep the window statistics comparable)
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; L=$P/stage_k6.log
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "stage K6 waiting for K5 $(date -u +%T)" > $L
while ! grep -q STAGEK5_DONE $P/stage_k5.log 2>/dev/null; do sleep 15; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
env LD_LIBRARY_PATH=$E/build NH_MT2=1 SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 valgrind --tool=callgrind --callgrind-out-file=$P/callgrind_step_v12.out --collect-atstart=yes --dump-instr=no $X/replay_sched6 8 1 4096 16384 $ACT > $P/step_v12_run.log 2>&1; echo "whole-step cg rc=$? $(grep Collected $P/step_v12_run.log) $(grep -oE 'steps=[0-9]+|turns=[0-9]+' $P/step_v12_run.log | tr '\n' ' ') $(date -u +%T)" >> $L
callgrind_annotate --inclusive=no --threshold=99.9 $P/callgrind_step_v12.out > $P/step_v12_self.txt 2>/dev/null
callgrind_annotate --tree=calling --threshold=99.9 $P/callgrind_step_v12.out > $P/step_v12_tree.txt 2>/dev/null
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_STATS=$P/mt2_cg4_stats.txt SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 valgrind --tool=callgrind --callgrind-out-file=$P/callgrind_mt2d.out --collect-atstart=no --dump-instr=no $X/replay_sched6 8 1 4096 16384 $ACT > $P/mt2_cg4_run.log 2>&1; echo "eligible-only v1.2 rc=$? $(grep Collected $P/mt2_cg4_run.log) $(head -1 $P/mt2_cg4_stats.txt) $(date -u +%T)" >> $L
callgrind_annotate --auto=yes --inclusive=no --threshold=100 --context=0 $P/callgrind_mt2d.out > $P/mt2d_lines.txt 2>/dev/null
M=$(awk '/eligible_moves/{print $2}' $P/mt2_cg4_stats.txt); python3 $P/lines_report.py $P/mt2d_lines.txt $M 5 > $P/mt2d_lines_report.txt
echo "STAGEK6_DONE $(date -u +%T)" >> $L
