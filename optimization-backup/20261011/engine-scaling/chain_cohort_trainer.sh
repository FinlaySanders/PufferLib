#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; H=/puffertank/experiments/nethack-24h-20261009
while [ "$(grep -c '^DONE' $S/inflat_campaign.log 2>/dev/null || echo 0)" -lt 4 ] && ! grep -q Traceback $S/inflat_campaign.log; do sleep 20; done
cd $H && python3 campaign_ablate.py ablate_cohort.json > $S/cohort_trainer_campaign.log 2>&1; echo COHORT_TRAINER_DONE
