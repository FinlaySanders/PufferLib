#!/bin/bash
# fobj2: build + verify replay + quick gates after chain J's native screen; line-level footprint of mload alongside;
# then native screen fobj2 vs mload once chain J's footprint arm is done, full gate, footprint arm + compare.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
while ! grep -q NATIVE_MLOAD_DONE $S/chain_j.log; do sleep 20; done; echo WAIT_NATIVE_MLOAD_DONE
cd $R && rm -rf $CS/engines/fobj2_verify && mkdir -p $CS/engines/fobj2_verify && cp -r $CS/engines/fobj2/source $CS/engines/fobj2_verify/source
(python3 build_candidate.py fobj2 || echo BUILD_FAILED fobj2) & (BUILD_EXTRA_CFLAGS=-DNLE_FOBJ_VERIFY python3 build_candidate.py fobj2_verify || echo BUILD_FAILED fobj2_verify) & wait; echo BUILD_FOBJ2_DONE
[ -f $CS/engines/fobj2/build/libnethack.so ] && [ -f $CS/engines/fobj2_verify/build/libnethack.so ] || { echo CHAINK_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/fobj2_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > fobj2_verify_run.log 2>&1
echo "VERIFY_FOBJ2 mismatches=$(grep -c FOBJ_MISMATCH fobj2_verify_run.log) $(grep RESULT fobj2_verify_run.log | cut -c1-140)"
cd $CS && nice -n 5 python3 check.py fobj2 --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_FOBJ2_DONE
cd $R && ./footprint_lines2.sh mload lines_mload; echo LINES_MLOAD_DONE
while ! grep -q FOOTPRINT_MLOAD_DONE $S/chain_j.log; do sleep 20; done; echo WAIT_FP_MLOAD_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/mload/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/fobj2/build $R/harness_incpack/replay fobj2; echo NATIVE_FOBJ2_DONE
cd $CS && nice -n 10 python3 check.py fobj2; echo FULLGATE_FOBJ2_DONE
cd $R && ./footprint_arm.sh $CS/engines/fobj2/build fp_fobj2 $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_mload fp_fobj2 2>/dev/null | tail -22 > FOOTPRINT_FOBJ2.md; echo FOOTPRINT_FOBJ2_DONE
