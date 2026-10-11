#!/bin/bash
# fold-in: wait for the misc1 PGO build, quick-gate it, run the trainer landing (12 arms, 3 regimes, ABBA), summarize.
R=/puffertank/experiments/nethack-engine-scaling-20261010; CS=/puffertank/experiments/nethack-compact-state-20261008; H=/puffertank/experiments/nethack-24h-20261009
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
while ! grep -q "PGO READY\|Traceback\|AssertionError" $S/pgo_misc1.log; do sleep 20; done
grep -q "PGO READY" $S/pgo_misc1.log || { echo PGO_FAILED; exit 1; }; echo PGO_MISC1_DONE
cd $CS && nice -n 5 python3 check.py misc1_pgo --quick 2>&1 | grep -E "^PASS|^FAIL|Traceback"; echo GATES_MISC1PGO_DONE
cd $H && python3 campaign_ablate.py ablate_landing3.json > $S/landing3_campaign.log 2>&1; echo LANDING3_RUN_DONE
cd $H && python3 summarize_ablate.py ablate_landing3.json 2>&1 | tail -n 40; echo LANDING3_DONE
