#!/bin/bash
# Stage 5 (after stage 4): candidate D = A + itsstuck reorder: PGO build, quick gates, native series base/selA/selD x2, full corpus hash.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; X=/puffertank/experiments/nethack-scheduler-20261012
L=$N/stage5.log; echo "stage5 waiting $(date -u +%T)" > $L
while ! grep -q STAGE4_DONE $N/stage4.log 2>/dev/null; do sleep 15; done
cd $N && python3 apply_D.py selD >> $L 2>&1 && diff -ru engines/selA/source engines/selD/source > engines/selD/changes_vs_A.patch
python3 build_pgo.py selD > engines/selD.build.out 2>&1; echo "D build: $(tail -1 engines/selD.build.out)" >> $L
ln -sfn $N/engines/selD $C/engines/lines_selD
(cd $C && timeout 900 python3 check.py --quick lines_selD > $N/gates_quick_selD.log 2>&1; echo "D quick gates rc=$? $(grep -c PASS $N/gates_quick_selD.log) passes" >> $L)
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
declare -A LIB=( [base]=$C/engines/tile_signed_pgo/build [selA]=$N/engines/selA/build [selD]=$N/engines/selD/build )
for rep in 1 2; do for e in base selA selD; do
  out=$N/native_rot16_${e}_d$rep.log
  env LD_LIBRARY_PATH=${LIB[$e]} SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 $e rep$rep $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L
done; done
(cd $C && timeout 3600 python3 check.py lines_selD > $N/gates_full_lines_selD.log 2>&1; echo "selD full gates rc=$? $(grep -E 'HASHES' $N/gates_full_lines_selD.log | tail -1) $(date -u +%T)" >> $L)
echo "STAGE5_DONE $(date -u +%T)" >> $L
