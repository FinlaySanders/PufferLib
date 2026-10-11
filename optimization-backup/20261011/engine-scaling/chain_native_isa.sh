#!/bin/bash
# Compiler-target check: mt7 source built with -march=native -mtune=native (AVX2/BMI2 on this i9-14900K) vs the generic x86-64 build.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && BUILD_EXTRA_CFLAGS="-march=native -mtune=native" python3 build_candidate.py mt7n || { echo BUILD_FAILED; exit 1; }; echo BUILD_mt7n_DONE
cd $CS && nice -n 5 python3 check.py mt7n --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_mt7n_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/mt7/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/mt7n/build $R/harness_incpack/replay mt7n; echo NATIVE_mt7n_DONE
cd $CS && nice -n 10 python3 check.py mt7n; echo FULLGATE_mt7n_DONE
echo CHAIN_mt7n_DONE
