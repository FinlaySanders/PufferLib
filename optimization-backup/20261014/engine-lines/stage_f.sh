#!/bin/bash
# Candidate F after the C2 validation: PGO build, quick gates, native E vs F x2 (cpu 2, rot 16), full corpus.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; X=/puffertank/experiments/nethack-scheduler-20261012; L=$N/stage_f.log
echo "stage F waiting $(date -u +%T)" > $L
while ! grep -q C2_DONE $N/stage_c2.log 2>/dev/null; do sleep 15; done
(cd $N && python3 build_pgo.py selF > engines/selF.build.out 2>&1); echo "F build: $(tail -1 $N/engines/selF.build.out)" >> $L
ln -sfn $N/engines/selF $C/engines/lines_selF
(cd $C && timeout 900 python3 check.py --quick lines_selF > $N/gates_quick_selF.log 2>&1; echo "F quick gates rc=$? $(grep -c PASS $N/gates_quick_selF.log) passes" >> $L)
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
for rep in 1 2; do for e in selE selF; do
  out=$N/native_rot16_${e}_f$rep.log
  env LD_LIBRARY_PATH=$N/engines/$e/build SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 $e rep$rep $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L
done; done
(cd $C && timeout 3600 python3 check.py lines_selF > $N/gates_full_lines_selF.log 2>&1; echo "selF full gates rc=$? $(grep -E 'HASHES' $N/gates_full_lines_selF.log | tail -1) $(date -u +%T)" >> $L)
echo "STAGEF_DONE $(date -u +%T)" >> $L
