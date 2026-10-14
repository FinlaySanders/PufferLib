#!/bin/bash
# Stage 1: wait for the B build, quick gates for B, native rotation-16 series (base/A/B x2, cpu 2), then full corpus hashes for A and B.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; X=/puffertank/experiments/nethack-scheduler-20261012
L=$N/stage1.log; echo "stage1 start $(date -u +%T)" > $L
while ! grep -q 'PGO READY\|Error\|AssertionError' $N/engines/selB.build.out 2>/dev/null; do sleep 5; done
grep -q 'PGO READY' $N/engines/selB.build.out || { echo "B BUILD FAILED" >> $L; tail -20 $N/engines/selB.build.out >> $L; }
if grep -q 'PGO READY' $N/engines/selB.build.out; then
  (cd $C && timeout 900 python3 check.py --quick lines_selB > $N/gates_quick_selB.log 2>&1; echo "B quick gates rc=$? $(grep -c PASS $N/gates_quick_selB.log) passes" >> $L)
fi
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
declare -A LIB=( [base]=$C/engines/tile_signed_pgo/build [selA]=$N/engines/selA/build [selB]=$N/engines/selB/build )
for rep in 1 2; do for e in base selA selB; do
  [ -f ${LIB[$e]}/libnethack.so ] || { echo "$e: no lib" >> $L; continue; }
  out=$N/native_rot16_${e}_$rep.log
  env LD_LIBRARY_PATH=${LIB[$e]} SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 $e rep$rep $(grep -oE ' sps=[^ ]+|busy_sps=[^ ]+|obs=[^ ]+|turns=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L
done; done
echo "NATIVE_SERIES_DONE $(date -u +%T)" >> $L
for e in lines_selA lines_selB; do
  (cd $C && timeout 3600 python3 check.py $e > $N/gates_full_$e.log 2>&1; echo "$e full gates rc=$? $(grep -E 'HASHES|PASS' $N/gates_full_$e.log | tail -2 | tr '\n' ' ') $(date -u +%T)" >> $L)
done
echo "STAGE1_DONE $(date -u +%T)" >> $L
