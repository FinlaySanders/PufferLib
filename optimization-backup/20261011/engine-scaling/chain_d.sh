#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
until grep -q REPORT_DONE $S/chain_c.log 2>/dev/null; do sleep 15; done
cd /puffertank/experiments/nethack-engine-scaling-20261010 && nice -n 5 python3 build_incstack_pgo.py && echo PGO_DONE || { echo PGO_FAILED; exit 1; }
cd /puffertank/experiments/nethack-compact-state-20261008 && nice -n 10 python3 check.py incstack_pgo --quick; echo GATES_PGO_DONE
cd /puffertank/experiments/nethack-engine-scaling-20261010 && ./native_screen2.sh /puffertank/experiments/nethack-compact-state-20261008/engines/incstack_pgo/build /puffertank/experiments/nethack-engine-scaling-20261010/harness_incpack/replay incstack_pgo; echo NATIVE4_DONE
cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py ablate_landing.json; echo LANDING_DONE
cd /puffertank/experiments/nethack-24h-20261009 && nice -n 19 python3 regime_report.py; echo REPORT2_DONE
