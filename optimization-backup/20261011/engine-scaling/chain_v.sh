#!/bin/bash
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && rm -rf $CS/engines/mt4_verify && mkdir -p $CS/engines/mt4_verify && cp -r $CS/engines/mt4/source $CS/engines/mt4_verify/source
(python3 build_candidate.py mt4 || echo BUILD_FAILED mt4) & (BUILD_EXTRA_CFLAGS="-DNLE_SPW_VERIFY -DNH_MOVEMENT_MASK_VERIFY" python3 build_candidate.py mt4_verify || echo BUILD_FAILED mt4_verify) & wait; echo BUILD_MT4_DONE
[ -f $CS/engines/mt4/build/libnethack.so ] && [ -f $CS/engines/mt4_verify/build/libnethack.so ] || { grep -m4 "error:" $CS/engines/mt4/build.log $CS/engines/mt4_verify/build.log | cut -c1-220; echo CHAINV_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/mt4_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > mt4_verify_run.log 2>&1
echo "VERIFY_MT4 mismatches=$(grep -c -i 'MISMATCH\|panic\|desync' mt4_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' mt4_verify_run.log)"
grep -i "MISMATCH\|panic\|desync" mt4_verify_run.log | sed 's/turn=[0-9]* //; s/at [0-9]*,[0-9]*//' | sort | uniq -c | sort -rn | head -8
cd $CS && nice -n 5 python3 check.py mt4 --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_MT4_DONE
while ! grep -q "CHAINU_DONE\|CHAINU_ABORT" $S/chain_u.log; do sleep 20; done; echo WAIT_CHAINU_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/mt3/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/mt4/build $R/harness_incpack/replay mt4; echo NATIVE_MT4_DONE
(cd $CS && nice -n 10 python3 check.py mt4; echo FULLGATE_MT4_DONE) & (cd $R && ./footprint_lines2.sh mt4 lines_mt4; echo LINES_MT4_DONE) & wait
cd $R && python3 ir_compare.py lines_mt3 lines_mt4 16; echo CHAINV_DONE
