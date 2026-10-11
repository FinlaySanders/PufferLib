#!/bin/bash
# invview2: after chain Q's native screen, stop chain Q (its full gate is known to fail), build pair, verify, gates, native screen vs misc1, full gate, footprint.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
export NETHACKDIR=/puffertank/experiments/nethack-perf-20260917/dat NH_ZT_MASK=0
while ! grep -q NATIVE_INVVIEW_DONE $S/chain_q.log; do sleep 20; done; echo WAIT_NATIVE_INVVIEW_DONE
pkill -f '[.]/chain_q[.]sh'; sleep 1; pkill -f 'check[.]py invvie[w]'; sleep 2; echo CHAINQ_STOPPED
cd $R && rm -rf $CS/engines/invview2_verify && mkdir -p $CS/engines/invview2_verify && cp -r $CS/engines/invview2/source $CS/engines/invview2_verify/source
(python3 build_candidate.py invview2 || echo BUILD_FAILED invview2) & (BUILD_EXTRA_CFLAGS=-DNLE_INVVIEW_VERIFY python3 build_candidate.py invview2_verify || echo BUILD_FAILED invview2_verify) & wait; echo BUILD_INVVIEW2_DONE
[ -f $CS/engines/invview2/build/libnethack.so ] && [ -f $CS/engines/invview2_verify/build/libnethack.so ] || { echo CHAINR_ABORT_BUILD; exit 1; }
LD_LIBRARY_PATH=$CS/engines/invview2_verify/build nice -n 5 ./harness_incpack/replay 512 32 0 32768 /puffertank/experiments/nethack-comprehensive-20261008/actions > invview2_verify_run.log 2>&1
echo "VERIFY_INVVIEW2 mismatches=$(grep -c MISMATCH invview2_verify_run.log) $(grep -o 'obs=[0-9a-f]* age=[0-9.]* turns=[0-9]*' invview2_verify_run.log)"
grep MISMATCH invview2_verify_run.log | sed 's/turn=[0-9]* //; s/slot=[0-9]* //' | sort | uniq -c | sort -rn | head -10
cd $CS && nice -n 5 python3 check.py invview2 --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_INVVIEW2_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/misc1/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/invview2/build $R/harness_incpack/replay invview2; echo NATIVE_INVVIEW2_DONE
cd $CS && nice -n 10 python3 check.py invview2; echo FULLGATE_INVVIEW2_DONE
cd $R && ./footprint_arm.sh $CS/engines/invview2/build fp_invview2 $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_misc1 fp_invview2 2>/dev/null | tail -22 > FOOTPRINT_INVVIEW2.md; echo FOOTPRINT_INVVIEW2_DONE
