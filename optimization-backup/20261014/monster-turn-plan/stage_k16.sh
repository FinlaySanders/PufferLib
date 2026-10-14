#!/bin/bash
# old-path profiles by rejection reason: 9 = near (distmin <= 9), 4 = asleep, 6 = status, 7 = species
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; L=$P/stage_k16.log
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
echo "stage K16 waiting for K15 $(date -u +%T)" > $L
while ! grep -q STAGEK15_DONE $P/stage_k15.log 2>/dev/null; do sleep 15; done
cd $P && python3 apply_mt2_whyfilter.py >> $L 2>&1
cmake --build $E/build_cg --target nethack -j8 > $E/build_cg_k16.log 2>&1; echo "cg build rc=$? errors=$(grep -c ' error' $E/build_cg_k16.log)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
for k in 9 4; do
  env LD_LIBRARY_PATH=$E/build_cg NH_MT2=1 NH_MT2_CG_INVERT=1 NH_MT2_CG_WHY=$k NH_MT2_STATS=$P/mt2_why${k}_stats.txt SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 valgrind --tool=callgrind --callgrind-out-file=$P/callgrind_why$k.out --collect-atstart=no --dump-instr=no $X/replay_sched6 8 1 4096 16384 $ACT > $P/why${k}_run.log 2>&1
  echo "why=$k rc=$? $(grep Collected $P/why${k}_run.log) collected_moves=$(grep '^mmoved3' -B70 $P/mt2_why${k}_stats.txt | head -0)$(awk '/^eligible_moves/{print " all="$4" elig="$2}' $P/mt2_why${k}_stats.txt) $(date -u +%T)" >> $L
  callgrind_annotate --inclusive=no --threshold=99.9 $P/callgrind_why$k.out > $P/why${k}_self.txt 2>/dev/null
  callgrind_annotate --auto=yes --inclusive=no --threshold=100 --context=0 $P/callgrind_why$k.out > $P/why${k}_lines.txt 2>/dev/null
done
echo "STAGEK16_DONE $(date -u +%T)" >> $L
