#!/bin/bash
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && rm -rf $CS/engines/mt2_verify && mkdir -p $CS/engines/mt2_verify && cp -r $CS/engines/mt2/source $CS/engines/mt2_verify/source
(python3 build_candidate.py mt2 || echo BUILD_FAILED mt2) & (BUILD_EXTRA_CFLAGS="-DNLE_SPW_VERIFY -DNH_MOVEMENT_MASK_VERIFY" python3 build_candidate.py mt2_verify || echo BUILD_FAILED mt2_verify) & wait; echo BUILD_MT2_DONE
[ -f $CS/engines/mt2/build/libnethack.so ] && [ -f $CS/engines/mt2_verify/build/libnethack.so ] || { grep -m3 "error:" $CS/engines/mt2/build.log $CS/engines/mt2_verify/build.log | cut -c1-220; echo CHAINT_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/mt2_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > mt2_verify_run.log 2>&1
echo "VERIFY_MT2 mismatches=$(grep -c MISMATCH mt2_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' mt2_verify_run.log)"
grep MISMATCH mt2_verify_run.log | sed 's/idx=[0-9]*//; s/turn=[0-9]* //' | sort | uniq -c | sort -rn | head -8
cd $CS && nice -n 5 python3 check.py mt2 --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_MT2_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/misc1/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/mt2/build $R/harness_incpack/replay mt2; echo NATIVE_MT2_DONE
(cd $CS && nice -n 10 python3 check.py mt2; echo FULLGATE_MT2_DONE) & (cd $R && ./footprint_lines2.sh mt2 lines_mt2; echo LINES_MT2_DONE) & wait
cd $R && python3 ir_compare.py lines_misc1 lines_mt2 16; echo CHAINT_DONE
