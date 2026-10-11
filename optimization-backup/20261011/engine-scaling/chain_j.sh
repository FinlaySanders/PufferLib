#!/bin/bash
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
while pgrep -f 'check.py mloa[d] --quick' >/dev/null; do sleep 10; done; echo GATES_MLOAD_DONE
while ! grep -q FOOTPRINT_INVWT_DONE $S/chain_i.log; do sleep 20; done; echo WAIT_FP_INVWT_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/invwt/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/mload/build $R/harness_incpack/replay mload; echo NATIVE_MLOAD_DONE
cd $CS && nice -n 10 python3 check.py mload; echo FULLGATE_MLOAD_DONE
cd $R && ./footprint_arm.sh $CS/engines/mload/build fp_mload $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_invwt fp_mload 2>/dev/null | tail -22 > FOOTPRINT_MLOAD.md; echo FOOTPRINT_MLOAD_DONE
