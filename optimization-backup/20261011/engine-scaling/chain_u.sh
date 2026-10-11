#!/bin/bash
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && rm -rf $CS/engines/mt3_verify && mkdir -p $CS/engines/mt3_verify && cp -r $CS/engines/mt3/source $CS/engines/mt3_verify/source
(python3 build_candidate.py mt3 || echo BUILD_FAILED mt3) & (BUILD_EXTRA_CFLAGS="-DNLE_SPW_VERIFY -DNH_MOVEMENT_MASK_VERIFY" python3 build_candidate.py mt3_verify || echo BUILD_FAILED mt3_verify) & wait; echo BUILD_MT3_DONE
[ -f $CS/engines/mt3/build/libnethack.so ] && [ -f $CS/engines/mt3_verify/build/libnethack.so ] || { grep -m3 "error:\|warning: always_inline" $CS/engines/mt3/build.log | cut -c1-200; echo CHAINU_ABORT_BUILD; exit 1; }
grep -c "always_inline" $CS/engines/mt3/build.log | sed 's/^/inline warnings: /'
LD_LIBRARY_PATH=$CS/engines/mt3_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > mt3_verify_run.log 2>&1
echo "VERIFY_MT3 mismatches=$(grep -c MISMATCH mt3_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' mt3_verify_run.log)"
cd $CS && nice -n 5 python3 check.py mt3 --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_MT3_DONE
while ! grep -q "CHAINT_DONE\|CHAINT_ABORT" $S/chain_t.log; do sleep 20; done; echo WAIT_CHAINT_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/mt2/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/mt3/build $R/harness_incpack/replay mt3; echo NATIVE_MT3_DONE
(cd $CS && nice -n 10 python3 check.py mt3; echo FULLGATE_MT3_DONE) & (cd $R && ./footprint_lines2.sh mt3 lines_mt3; echo LINES_MT3_DONE) & wait
cd $R && python3 ir_compare.py lines_mt2 lines_mt3 16; echo CHAINU_DONE
