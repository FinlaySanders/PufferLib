#!/bin/bash
# misc1: build pair, verify replay, quick gates; native screen vs fobj2 after chain K2's footprint arm; full gate; footprint arm + compare.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && rm -rf $CS/engines/misc1_verify && mkdir -p $CS/engines/misc1_verify && cp -r $CS/engines/misc1/source $CS/engines/misc1_verify/source
(python3 build_candidate.py misc1 || echo BUILD_FAILED misc1) & (BUILD_EXTRA_CFLAGS=-DNLE_MISC_VERIFY python3 build_candidate.py misc1_verify || echo BUILD_FAILED misc1_verify) & wait; echo BUILD_MISC1_DONE
[ -f $CS/engines/misc1/build/libnethack.so ] && [ -f $CS/engines/misc1_verify/build/libnethack.so ] || { echo CHAINL_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/misc1_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > misc1_verify_run.log 2>&1
echo "VERIFY_MISC1 mismatches=$(grep -c MISMATCH misc1_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' misc1_verify_run.log)"
cd $CS && nice -n 5 python3 check.py misc1 --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_MISC1_DONE
while ! grep -q "FOOTPRINT_FOBJ2_DONE" $S/chain_k2.log; do sleep 20; done; echo WAIT_FP_FOBJ2_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/fobj2/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/misc1/build $R/harness_incpack/replay misc1; echo NATIVE_MISC1_DONE
cd $CS && nice -n 10 python3 check.py misc1; echo FULLGATE_MISC1_DONE
cd $R && ./footprint_arm.sh $CS/engines/misc1/build fp_misc1 $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_fobj2 fp_misc1 2>/dev/null | tail -22 > FOOTPRINT_MISC1.md; echo FOOTPRINT_MISC1_DONE
