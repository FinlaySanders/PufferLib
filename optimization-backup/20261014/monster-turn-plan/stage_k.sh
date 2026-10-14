#!/bin/bash
# kernel validation chain: trace build, quick gates, same-binary rotation-16 A/B (NH_MT2=0 vs 1), full corpus hash
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; E=$P/engines/mt2; X=/puffertank/experiments/nethack-scheduler-20261012; C=/puffertank/experiments/nethack-compact-state-20261008
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions; L=$P/stage_k.log
echo "stage K start $(date -u +%T)" > $L
F="-fno-semantic-interposition -g -DNH_MT2_TRACE"
cmake -S $E/source -B $E/build_trace -DCMAKE_BUILD_TYPE=Release -DNLE_TLS_INITIAL_EXEC=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON "-DCMAKE_C_FLAGS=$F" "-DCMAKE_CXX_FLAGS=$F" -DFETCHCONTENT_SOURCE_DIR_BZIP2=/puffertank/pufferlib/vendor/fast-nle/build/_deps/bzip2-src -DFETCHCONTENT_SOURCE_DIR_DEBOOST_CONTEXT=/puffertank/pufferlib/vendor/fast-nle/build/_deps/deboost_context-src -DFETCHCONTENT_SOURCE_DIR_PYBIND11=/puffertank/pufferlib/vendor/fast-nle/build/_deps/pybind11-src > $E/configure_trace.log 2>&1 && cmake --build $E/build_trace --target nethack -j8 > $E/build_trace.log 2>&1; echo "trace build rc=$? $(date -u +%T)" >> $L
cd $C && python3 check.py --quick lines_mt2 > $P/mt2_gates_k.log 2>&1; echo "quick gates rc=$? passes=$(grep -c '^PASS' $P/mt2_gates_k.log) $(date -u +%T)" >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
for rep in 1 2; do for f in 0 1; do
  env LD_LIBRARY_PATH=$E/build NH_MT2=$f SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $P/ab_k_${f}_${rep}.log 2>&1
  echo "NATIVE rot16 NH_MT2=$f rep$rep $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $P/ab_k_${f}_${rep}.log | tr '\n' ' ') $(date -u +%T)" >> $L
done; done
if grep -q "quick gates rc=0" $L; then cd $C && python3 check.py --hash-only lines_mt2 > $P/mt2_gates_full.log 2>&1; echo "full hash rc=$? $(grep HASHES $P/mt2_gates_full.log) $(date -u +%T)" >> $L; fi
echo "STAGEK_DONE $(date -u +%T)" >> $L
