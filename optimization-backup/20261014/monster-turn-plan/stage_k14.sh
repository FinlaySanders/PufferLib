#!/bin/bash
# re-rank with kernel v1.4: whole-step profile (kernel on) + old-path-only profile (moves the fast path rejects)
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; L=$P/stage_k14.log
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "stage K14 start $(date -u +%T)" > $L
cmake --build $E/build_cg --target nethack -j8 > $E/build_cg_k14.log 2>&1; echo "cg build rc=$? errors=$(grep -c ' error' $E/build_cg_k14.log)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
env LD_LIBRARY_PATH=$E/build NH_MT2=1 SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 valgrind --tool=callgrind --callgrind-out-file=$P/callgrind_step_v14.out --collect-atstart=yes --dump-instr=no $X/replay_sched6 8 1 4096 16384 $ACT > $P/step_v14_run.log 2>&1; echo "whole-step v1.4 rc=$? $(grep Collected $P/step_v14_run.log) $(date -u +%T)" >> $L
callgrind_annotate --inclusive=no --threshold=99.9 $P/callgrind_step_v14.out > $P/step_v14_self.txt 2>/dev/null
callgrind_annotate --tree=calling --threshold=99.9 $P/callgrind_step_v14.out > $P/step_v14_tree.txt 2>/dev/null
python3 $P/step_buckets.py $P/step_v14_self.txt 163840 > $P/step_v14_buckets.txt 2>&1
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_CG_INVERT=1 NH_MT2_STATS=$P/mt2_cg5_stats.txt SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 valgrind --tool=callgrind --callgrind-out-file=$P/callgrind_old.out --collect-atstart=no --dump-instr=no $X/replay_sched6 8 1 4096 16384 $ACT > $P/mt2_cg5_run.log 2>&1; echo "old-path-only rc=$? $(grep Collected $P/mt2_cg5_run.log) $(head -1 $P/mt2_cg5_stats.txt) $(date -u +%T)" >> $L
callgrind_annotate --inclusive=no --threshold=99.9 $P/callgrind_old.out > $P/old_self.txt 2>/dev/null
callgrind_annotate --tree=calling --threshold=99.9 $P/callgrind_old.out > $P/old_tree.txt 2>/dev/null
echo "STAGEK14_DONE $(date -u +%T)" >> $L
