#!/bin/bash
cd /puffertank/experiments/nethack-compact-state-20261008 && nice -n 10 python3 check.py incstack2; echo FULLGATE2_DONE
cd /puffertank/experiments/nethack-engine-scaling-20261010 && nice -n 5 python3 build_incstack2_pgo.py && echo PGO2_DONE || { echo PGO2_FAILED; exit 1; }
cd /puffertank/experiments/nethack-compact-state-20261008 && nice -n 10 python3 check.py incstack2_pgo --quick; echo GATES_PGO2_DONE
cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py ablate_landing2.json; echo LANDING2_DONE
cd /puffertank/experiments/nethack-engine-scaling-20261010 && ./native_screen2.sh /puffertank/experiments/nethack-compact-state-20261008/engines/incstack2_pgo/build /puffertank/experiments/nethack-engine-scaling-20261010/harness_incpack/replay incstack2_pgo; echo NATIVE5_DONE
cd /puffertank/experiments/nethack-24h-20261009 && nice -n 19 python3 regime_report.py; echo REPORT3_DONE
