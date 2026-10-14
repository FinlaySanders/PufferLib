#!/bin/bash
# whole-step profile with the C2 header harness (landed mask code) + mt2 engine: what is left in pack_obs after C2
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; HC=/puffertank/experiments/nethack-engine-lines-20261014; L=$P/stage_k9.log
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "stage K9 waiting for K8 $(date -u +%T)" > $L
while ! grep -q STAGEK8_DONE $P/stage_k8.log 2>/dev/null; do sleep 15; done
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
env LD_LIBRARY_PATH=$E/build NH_MT2=1 SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 valgrind --tool=callgrind --callgrind-out-file=$P/callgrind_step_c2.out --collect-atstart=yes --dump-instr=no $HC/replay_sched6_C2 8 1 4096 16384 $ACT > $P/step_c2_run.log 2>&1; echo "C2 whole-step cg rc=$? $(grep Collected $P/step_c2_run.log) $(grep -oE 'obs=[^ ]+' $P/step_c2_run.log) $(date -u +%T)" >> $L
callgrind_annotate --inclusive=no --threshold=99.9 $P/callgrind_step_c2.out > $P/step_c2_self.txt 2>/dev/null
callgrind_annotate --auto=yes --inclusive=no --threshold=100 --context=0 $P/callgrind_step_c2.out > $P/step_c2_lines.txt 2>/dev/null
python3 $P/step_buckets.py $P/step_c2_self.txt 163840 > $P/step_c2_buckets.txt 2>&1
python3 $P/lines_report.py $P/step_c2_lines.txt 163840 150 > $P/step_c2_lines_report.txt 2>&1
echo "STAGEK9_DONE $(date -u +%T)" >> $L
