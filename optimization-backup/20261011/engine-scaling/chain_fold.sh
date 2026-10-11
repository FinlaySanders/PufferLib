#!/bin/bash
# Final fold of a Phase 3 stack: chain_fold.sh <final_engine> <tag>
# PGO build, quick gates on the PGO .so, trainer landing vs misc1_pgo (ABBA, 3 regimes), summary, final instruction census vs misc1.
F=$1; T=$2
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008; H=/puffertank/experiments/nethack-24h-20261009
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
cd $R && rm -rf $CS/engines/${F}_pgo && python3 build_pgo.py $F > $S/pgo_$F.log 2>&1; grep -q "PGO READY" $S/pgo_$F.log || { echo PGO_FAILED; exit 1; }; echo PGO_${F}_DONE
cd $CS && nice -n 5 python3 check.py ${F}_pgo --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_${F}PGO_DONE
cd $R && python3 make_landing.py $CS/engines/${F}_pgo/build $T $CS/engines/misc1_pgo/build
cd $H && python3 campaign_ablate.py ablate_$T.json > $S/${T}_campaign.log 2>&1; echo LANDING_RUN_DONE
grep -E "^DONE" $S/${T}_campaign.log | cut -c1-80
cd $R && python3 ir_compare.py lines_misc1 lines_$F 12; echo FOLD_DONE
