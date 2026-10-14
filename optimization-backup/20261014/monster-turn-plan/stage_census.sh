#!/bin/bash
# M1/M3/M4 census after the BOLT pipeline: LTO build of the instrumented engine, rotation-16 harness run (128 games, warm 4096, measure 16384)
# dumping NH_CENSUS; then a small callgrind pass for callee counts inside m_move/mfndpos.
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; N=/puffertank/experiments/nethack-engine-lines-20261014; X=/puffertank/experiments/nethack-scheduler-20261012; L=$P/census.log
echo "census waiting $(date -u +%T)" > $L
while ! grep -q STAGEBOLT_DONE $N/stage_bolt.log 2>/dev/null; do sleep 15; done
cd $P && python3 apply_census.py >> $L 2>&1 || { echo "APPLY FAILED" >> $L; exit 1; }
E=$P/engines/census; F="-fno-semantic-interposition -g"
cmake -S $E/source -B $E/build -DCMAKE_BUILD_TYPE=Release -DNLE_TLS_INITIAL_EXEC=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON "-DCMAKE_C_FLAGS=$F" "-DCMAKE_CXX_FLAGS=$F" -DFETCHCONTENT_SOURCE_DIR_BZIP2=/puffertank/pufferlib/vendor/fast-nle/build/_deps/bzip2-src -DFETCHCONTENT_SOURCE_DIR_DEBOOST_CONTEXT=/puffertank/pufferlib/vendor/fast-nle/build/_deps/deboost_context-src -DFETCHCONTENT_SOURCE_DIR_PYBIND11=/puffertank/pufferlib/vendor/fast-nle/build/_deps/pybind11-src > $E/configure.log 2>&1 && cmake --build $E/build --target nethack -j8 > $E/build.log 2>&1; echo "census build rc=$? $(date -u +%T)" >> $L
grep -n ' error' $E/build.log | head -3 >> $L
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
ACT=/puffertank/experiments/nethack-comprehensive-20261008/actions
env LD_LIBRARY_PATH=$E/build NH_CENSUS=$P/census_rot16.txt SCHED_C=1 SCHED_A=16 SCHED_GROUPFILL=1 SCHED_SEG=16384 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 taskset -c 2 $X/replay_sched6 128 1 4096 16384 $ACT > $P/census_run.log 2>&1
echo "census run: $(grep -oE ' sps=[^ ]+|obs=[^ ]+' $P/census_run.log | tr '\n' ' ') lines $(wc -l < $P/census_rot16.txt 2>/dev/null)" >> $L
# M3: callgrind callee counts (small workload: 8 games, warm 512, measure 256 ticks)
env LD_LIBRARY_PATH=$N/engines/selE/build SCHED_C=1 SCHED_A=8 SCHED_GROUPFILL=1 SCHED_SEG=256 SCHED_PIN=0 SCHED_STEAL=0 SCHED_FWD_US=0 valgrind --tool=callgrind --callgrind-out-file=$P/callgrind.out --collect-atstart=yes $X/replay_sched6 8 1 512 256 $ACT > $P/callgrind_run.log 2>&1; echo "callgrind rc=$? $(date -u +%T)" >> $L
callgrind_annotate --inclusive=yes --threshold=99.9 $P/callgrind.out > $P/callgrind_inclusive.txt 2>&1
callgrind_annotate --tree=calling --threshold=99.9 $P/callgrind.out > $P/callgrind_tree.txt 2>&1
echo "CENSUS_DONE $(date -u +%T)" >> $L
