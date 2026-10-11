#!/bin/bash
# kbits (+ misc1 re-screen): build pair + verify + quick gates after chain M's native screen; native screen vs mbits after chain M's footprint; full gate; footprint.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
while ! grep -q NATIVE_MBITS_DONE $S/chain_m.log; do sleep 20; done; echo WAIT_NATIVE_MBITS_DONE
cd $R && rm -rf $CS/engines/kbits_verify && mkdir -p $CS/engines/kbits_verify && cp -r $CS/engines/kbits/source $CS/engines/kbits_verify/source
(python3 build_candidate.py kbits || echo BUILD_FAILED kbits) & (BUILD_EXTRA_CFLAGS=-DNLE_KBITS_VERIFY python3 build_candidate.py kbits_verify || echo BUILD_FAILED kbits_verify) & wait; echo BUILD_KBITS_DONE
[ -f $CS/engines/kbits/build/libnethack.so ] && [ -f $CS/engines/kbits_verify/build/libnethack.so ] || { echo CHAINN_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/kbits_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > kbits_verify_run.log 2>&1
echo "VERIFY_KBITS mismatches=$(grep -c MISMATCH kbits_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' kbits_verify_run.log)"
cd $CS && nice -n 5 python3 check.py kbits --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_KBITS_DONE
while ! grep -q FOOTPRINT_MBITS_DONE $S/chain_m.log; do sleep 20; done; echo WAIT_FP_MBITS_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/fobj2/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/misc1/build $R/harness_incpack/replay misc1b; echo NATIVE_MISC1B_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/mbits/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/kbits/build $R/harness_incpack/replay kbits; echo NATIVE_KBITS_DONE
cd $CS && nice -n 10 python3 check.py kbits; echo FULLGATE_KBITS_DONE
cd $R && ./footprint_arm.sh $CS/engines/kbits/build fp_kbits $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_mbits fp_kbits 2>/dev/null | tail -22 > FOOTPRINT_KBITS.md; echo FOOTPRINT_KBITS_DONE
