#!/bin/bash
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
while pgrep -f 'check.py invw[t] --quick' >/dev/null; do sleep 10; done; echo GATES_INVWT_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/heat1/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/invwt/build $R/harness_incpack/replay invwt; echo NATIVE_INVWT_DONE
cd $CS && nice -n 10 python3 check.py invwt; echo FULLGATE_INVWT_DONE
cd $R && ./footprint_arm.sh $CS/engines/invwt/build fp_invwt $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_heat1 fp_invwt 2>/dev/null | tail -22 > FOOTPRINT_INVWT.md; echo FOOTPRINT_INVWT_DONE
