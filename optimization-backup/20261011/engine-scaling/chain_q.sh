#!/bin/bash
# invview (on misc1): build pair, verify replay, quick gates; wait for the lines_misc1 callgrind; native screen vs misc1; full gate; footprint.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
cd $R && rm -rf $CS/engines/invview_verify && mkdir -p $CS/engines/invview_verify && cp -r $CS/engines/invview/source $CS/engines/invview_verify/source
(python3 build_candidate.py invview || echo BUILD_FAILED invview) & (BUILD_EXTRA_CFLAGS=-DNLE_INVVIEW_VERIFY python3 build_candidate.py invview_verify || echo BUILD_FAILED invview_verify) & wait; echo BUILD_INVVIEW_DONE
[ -f $CS/engines/invview/build/libnethack.so ] && [ -f $CS/engines/invview_verify/build/libnethack.so ] || { echo CHAINQ_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/invview_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > invview_verify_run.log 2>&1
echo "VERIFY_INVVIEW mismatches=$(grep -c MISMATCH invview_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' invview_verify_run.log)"
grep MISMATCH invview_verify_run.log | sed 's/turn=[0-9]* //' | sort | uniq -c | sort -rn | head -8
cd $CS && nice -n 5 python3 check.py invview --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_INVVIEW_DONE
while ! grep -q "LINES_DONE lines_misc1" $S/lines_misc1.log; do sleep 20; done; echo WAIT_LINES_MISC1_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/misc1/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/invview/build $R/harness_incpack/replay invview; echo NATIVE_INVVIEW_DONE
cd $CS && nice -n 10 python3 check.py invview; echo FULLGATE_INVVIEW_DONE
cd $R && ./footprint_arm.sh $CS/engines/invview/build fp_invview $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_misc1 fp_invview 2>/dev/null | tail -22 > FOOTPRINT_INVVIEW.md; echo FOOTPRINT_INVVIEW_DONE
