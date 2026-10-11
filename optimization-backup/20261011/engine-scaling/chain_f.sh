#!/bin/bash
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008
cd $CS && nice -n 10 python3 check.py heat1 --quick; echo GATES_HEAT1_DONE
cd $R && CTRL_OVERRIDE=$CS/engines/incstack2/build CTRLREPLAY_OVERRIDE=$R/harness_incpack/replay ./native_screen2.sh $CS/engines/heat1/build $R/harness_incpack/replay heat1; echo NATIVE_HEAT1_DONE
cd $R && ./footprint_arm.sh $CS/engines/incstack2/build fp_incstack2 $R/harness_incpack/replay; ./footprint_arm.sh $CS/engines/heat1/build fp_heat1 $R/harness_incpack/replay
cd $R && nice -n 19 python3 footprint_compare.py fp_incstack2 fp_heat1 > FOOTPRINT_HEAT1.md 2>&1; echo FOOTPRINT_HEAT1_DONE
