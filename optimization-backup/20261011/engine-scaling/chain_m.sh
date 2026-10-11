#!/bin/bash
# mbits: build pair + verify + quick gates after chain L's native screen; native screen vs misc1 after chain L's footprint; full gate; footprint.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
while ! grep -q NATIVE_MISC1_DONE $S/chain_l.log; do sleep 20; done; echo WAIT_NATIVE_MISC1_DONE
cd $R && rm -rf $CS/engines/mbits_verify && mkdir -p $CS/engines/mbits_verify && cp -r $CS/engines/mbits/source $CS/engines/mbits_verify/source
(python3 build_candidate.py mbits || echo BUILD_FAILED mbits) & (BUILD_EXTRA_CFLAGS=-DNLE_MBITS_VERIFY python3 build_candidate.py mbits_verify || echo BUILD_FAILED mbits_verify) & wait; echo BUILD_MBITS_DONE
[ -f $CS/engines/mbits/build/libnethack.so ] && [ -f $CS/engines/mbits_verify/build/libnethack.so ] || { echo CHAINM_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/mbits_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > mbits_verify_run.log 2>&1
echo "VERIFY_MBITS mismatches=$(grep -c MISMATCH mbits_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' mbits_verify_run.log)"
cd $CS && nice -n 5 python3 check.py mbits --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_MBITS_DONE
while ! grep -q FOOTPRINT_MISC1_DONE $S/chain_l.log; do sleep 20; done; echo WAIT_FP_MISC1_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/misc1/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/mbits/build $R/harness_incpack/replay mbits; echo NATIVE_MBITS_DONE
cd $CS && nice -n 10 python3 check.py mbits; echo FULLGATE_MBITS_DONE
cd $R && ./footprint_arm.sh $CS/engines/mbits/build fp_mbits $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_misc1 fp_mbits 2>/dev/null | tail -22 > FOOTPRINT_MBITS.md; echo FOOTPRINT_MBITS_DONE
