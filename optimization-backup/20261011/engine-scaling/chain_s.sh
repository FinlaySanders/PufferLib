#!/bin/bash
# mt1 (terrain LUT in mfndpos): build pair, verify replay (reference query twin), quick gates, native screen vs misc1, instruction census, full gate.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && rm -rf $CS/engines/mt1_verify && mkdir -p $CS/engines/mt1_verify && cp -r $CS/engines/mt1/source $CS/engines/mt1_verify/source
(python3 build_candidate.py mt1 || echo BUILD_FAILED mt1) & (BUILD_EXTRA_CFLAGS=-DNH_MOVEMENT_MASK_VERIFY python3 build_candidate.py mt1_verify || echo BUILD_FAILED mt1_verify) & wait; echo BUILD_MT1_DONE
[ -f $CS/engines/mt1/build/libnethack.so ] && [ -f $CS/engines/mt1_verify/build/libnethack.so ] || { echo CHAINS_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/mt1_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > mt1_verify_run.log 2>&1
echo "VERIFY_MT1 mismatches=$(grep -c MISMATCH mt1_verify_run.log) panics=$(grep -c -i 'panic\|mismatch at' mt1_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' mt1_verify_run.log)"
grep -i "MISMATCH\|panic" mt1_verify_run.log | head -5
cd $CS && nice -n 5 python3 check.py mt1 --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_MT1_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/misc1/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/mt1/build $R/harness_incpack/replay mt1; echo NATIVE_MT1_DONE
(cd $CS && nice -n 10 python3 check.py mt1; echo FULLGATE_MT1_DONE) & (cd $R && ./footprint_lines2.sh mt1 lines_mt1; echo LINES_MT1_DONE) & wait
echo CHAINS_DONE
