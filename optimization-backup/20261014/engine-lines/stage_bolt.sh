#!/bin/bash
# BOLT post-link layout on top of PGO (instrumentation mode): PGO build with relocations (-Wl,-q), instrument, profile on the harness workload,
# optimise, gate, native A/B vs the plain PGO engine. Runs after candidate F's pipeline.
N=/puffertank/experiments/nethack-engine-lines-20261014; C=/puffertank/experiments/nethack-compact-state-20261008; X=/puffertank/experiments/nethack-scheduler-20261012; L=$N/stage_bolt.log
BOLT=/usr/lib/llvm-18/bin/llvm-bolt; MERGE=/usr/lib/llvm-18/bin/merge-fdata
echo "bolt waiting $(date -u +%T)" > $L
while ! grep -q STAGEF_DONE $N/stage_f.log 2>/dev/null; do sleep 15; done
rm -rf $N/engines/fastnle_ade_q; mkdir -p $N/engines/fastnle_ade_q; cp -r $N/engines/fastnle_ade/source $N/engines/fastnle_ade_q/source
(cd $N && python3 build_pgo.py fastnle_ade_q -Wl,-q > engines/fastnle_ade_q.build.out 2>&1); echo "relocs build: $(tail -1 $N/engines/fastnle_ade_q.build.out)" >> $L
SO=$N/engines/fastnle_ade_q/build/libnethack.so; echo "rela sections: $(readelf -S $SO | grep -c '\.rela\.text')" >> $L
B=$N/engines/fastnle_bolt; rm -rf $B; mkdir -p $B/inst $B/build $B/prof
$BOLT $SO -instrument -o $B/inst/libnethack.so --instrumentation-file=$B/prof/prof.fdata --instrumentation-file-append-pid > $B/instrument.log 2>&1; echo "instrument rc=$? $(tail -1 $B/instrument.log | cut -c1-120)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
env LD_LIBRARY_PATH=$B/inst SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $B/profile_run.log 2>&1; echo "profile run: $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $B/profile_run.log | tr '\n' ' ') fdata files: $(ls $B/prof | wc -l)" >> $L
if [ $(ls $B/prof/*.fdata 2>/dev/null | wc -l) -gt 1 ]; then $MERGE $B/prof/*.fdata > $B/prof/merged.fdata 2>> $L; else cp $B/prof/*.fdata $B/prof/merged.fdata; fi
$BOLT $SO -o $B/build/libnethack.so -data=$B/prof/merged.fdata -reorder-blocks=ext-tsp -reorder-functions=hfsort+ -split-functions -split-all-cold -split-eh -icf=1 -use-gnu-stack -dyno-stats > $B/bolt.log 2>&1; echo "bolt rc=$? $(grep -iE 'BOLT-INFO: (.*functions were overwritten|.*basic blocks)' $B/bolt.log | head -2 | tr '\n' ' ' | cut -c1-200)" >> $L
[ -f $B/build/libnethack.so ] || { echo "NO BOLTED LIB" >> $L; echo "STAGEBOLT_DONE" >> $L; exit 1; }
ln -sfn $B $C/engines/lines_fastnle_bolt
(cd $C && timeout 900 python3 check.py --quick lines_fastnle_bolt > $N/gates_quick_bolt.log 2>&1; echo "bolt quick gates rc=$? $(grep -c PASS $N/gates_quick_bolt.log) passes" >> $L)
for rep in 1 2; do for e in fastnle_ade fastnle_ade_q fastnle_bolt; do
  out=$N/native_rot16_${e}_bolt$rep.log
  env LD_LIBRARY_PATH=$N/engines/$e/build SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 cpu2 $e rep$rep $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L
done; done
for e in fastnle_ade fastnle_bolt; do out=$N/native_rot16_${e}_boltE.log
  env LD_LIBRARY_PATH=$N/engines/$e/build SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 16 $X/replay_sched6 128 1 4096 16384 $ACT > $out 2>&1
  echo "NATIVE rot16 cpu16 $e $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $out | tr '\n' ' ') $(date -u +%T)" >> $L; done
if grep -q 'rc=0 5 passes' $L; then (cd $C && timeout 3600 python3 check.py lines_fastnle_bolt > $N/gates_full_bolt.log 2>&1; echo "bolt full gates rc=$? $(grep -E 'HASHES' $N/gates_full_bolt.log | tail -1) $(date -u +%T)" >> $L); fi
echo "STAGEBOLT_DONE $(date -u +%T)" >> $L
