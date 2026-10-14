#!/bin/bash
# Stage 7 (after stage 6): candidate E = D + track-match mask + squeeze mask: PGO build, quick gates, native base/selD/selE x2, full corpus.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; X=/puffertank/experiments/nethack-scheduler-20261012
L=$N/stage7.log; echo "stage7 waiting $(date -u +%T)" > $L
while ! grep -q STAGE6_DONE $N/stage6.log 2>/dev/null; do sleep 15; done
cd $N && python3 apply_E.py selE >> $L 2>&1 && diff -ru engines/selD/source engines/selE/source > engines/selE/changes_vs_D.patch
python3 build_pgo.py selE > engines/selE.build.out 2>&1; echo "E build: $(tail -1 engines/selE.build.out)" >> $L
ln -sfn $N/engines/selE $C/engines/lines_selE
(cd $C && timeout 900 python3 check.py --quick lines_selE > $N/gates_quick_selE.log 2>&1; echo "E quick gates rc=$? $(grep -c PASS $N/gates_quick_selE.log) passes" >> $L)
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
declare -A LIB=( [base]=$C/engines/tile_signed_pgo/build [selD]=$N/engines/selD/build [selE]=$N/engines/selE/build )
for rep in 1 2; do for e in base selD selE; do
  out=$N/native_rot16_${e}_e$rep.log
  env LD_LIBRARY_PATH=${LIB[$e]} SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 $e rep$rep $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L
done; done
(cd $C && timeout 3600 python3 check.py lines_selE > $N/gates_full_lines_selE.log 2>&1; echo "selE full gates rc=$? $(grep -E 'HASHES' $N/gates_full_lines_selE.log | tail -1) $(date -u +%T)" >> $L)
echo "STAGE7_DONE $(date -u +%T)" >> $L
