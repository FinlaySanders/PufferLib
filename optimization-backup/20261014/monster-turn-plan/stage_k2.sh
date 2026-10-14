#!/bin/bash
# rebuild the three mt2 variants after the trace-hook fix, re-run quick gates, then callgrind the NEW path (eligible moves only)
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_k2.log
echo "stage K2 start $(date -u +%T)" > $L
cmake --build $E/build --target nethack -j8 > $E/build_k2.log 2>&1; echo "plain rebuild rc=$?" >> $L
cmake --build $E/build_trace --target nethack -j8 > $E/build_trace2.log 2>&1; echo "trace rebuild rc=$? $(grep -c ' error' $E/build_trace2.log)" >> $L
cmake --build $E/build_cg --target nethack -j8 > $E/build_cg4.log 2>&1; echo "cg rebuild rc=$? $(grep -c ' error' $E/build_cg4.log)" >> $L
cd $C && python3 check.py --quick lines_mt2 > $P/mt2_gates_k2.log 2>&1; echo "quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2_gates_k2.log) $(date -u +%T)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_STATS=$P/mt2_cg3_stats.txt SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 valgrind --tool=callgrind --callgrind-out-file=$P/callgrind_mt2c.out --collect-atstart=no --dump-instr=no $X/replay_sched6 8 1 4096 16384 $ACT > $P/mt2_cg3_run.log 2>&1; echo "cg new-path rc=$? $(grep Collected $P/mt2_cg3_run.log) $(cat $P/mt2_cg3_stats.txt | head -1) $(date -u +%T)" >> $L
callgrind_annotate --auto=yes --inclusive=no --threshold=100 --context=0 $P/callgrind_mt2c.out > $P/mt2c_lines.txt 2>/dev/null
M=$(awk '/eligible_moves/{print $2}' $P/mt2_cg3_stats.txt); python3 $P/lines_report.py $P/mt2c_lines.txt $M 5 > $P/mt2c_lines_report.txt
echo "STAGEK2_DONE $(date -u +%T)" >> $L
