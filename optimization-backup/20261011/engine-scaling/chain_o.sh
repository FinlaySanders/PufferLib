#!/bin/bash
# kbits (on misc1): verify replay, quick gates; misc1 re-screen vs fobj2; kbits screen vs misc1; full gate; footprint arm + compare.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && LD_LIBRARY_PATH=$CS/engines/kbits_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > kbits_verify_run.log 2>&1
echo "VERIFY_KBITS mismatches=$(grep -c MISMATCH kbits_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' kbits_verify_run.log)"
cd $CS && nice -n 5 python3 check.py kbits --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_KBITS_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/fobj2/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/misc1/build $R/harness_incpack/replay misc1b; echo NATIVE_MISC1B_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/misc1/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/kbits/build $R/harness_incpack/replay kbits; echo NATIVE_KBITS_DONE
cd $CS && nice -n 10 python3 check.py kbits; echo FULLGATE_KBITS_DONE
cd $R && ./footprint_arm.sh $CS/engines/kbits/build fp_kbits $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_misc1 fp_kbits 2>/dev/null | tail -22 > FOOTPRINT_KBITS.md; echo FOOTPRINT_KBITS_DONE
