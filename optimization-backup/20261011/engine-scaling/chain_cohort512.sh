#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q "CHAIN_mt8_DONE\|CHAIN_ABORT" $S/chain_mt8.log; do sleep 30; done
cd $H && python3 campaign_ablate.py ablate_cohort512.json > $S/cohort512_campaign.log 2>&1; grep -E "^DONE" $S/cohort512_campaign.log | cut -c1-80; echo COHORT512_DONE
