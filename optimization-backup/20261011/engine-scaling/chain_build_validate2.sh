#!/bin/bash
# retry: build with the reference binary's extra flags; wait for the branch census; util3; ini validation; proof comparison
R=/puffertank/experiments/nethack-engine-scaling-20261010; T=$R/trainer_cohort; H=/puffertank/experiments/nethack-24h-20261009; S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
J=$(find /puffertank/experiments -maxdepth 2 -name "incpack_v39-build.json" 2>/dev/null | head -1); [ -n "$J" ] || J=$H/attribution_v37-build.json
BASE=$(cat $T/build_flags.txt | tr -d '\n'); FULL=$(python3 -c "import json;print(json.load(open('$J'))['flags'])"); EXTRA=${FULL#$BASE}; echo "EXTRA_FLAGS from $(basename $J): $EXTRA"
cd $T && rm -rf snapshots/cohort_ini && python3 build.py cohort_ini $EXTRA > $T/build_cohort_ini.out 2>&1; rc=$?; echo "BUILD_cohort_ini rc=$rc $(date -u +%T)"
[ $rc -eq 0 ] || { grep -m5 "error" $T/cohort_ini-build.log | cut -c1-200; echo CHAIN_ABORT_BUILD2; exit 1; }
ln -sfn $T/binaries/cohort_ini $H/binaries/cohort_ini
while ! grep -q "BRANCH_DONE\|FAILED" $S/chain_branch.log 2>/dev/null; do sleep 15; done; echo "WAIT_BRANCH_DONE $(date -u +%T)"
$R/chain_util3.sh; echo "UTIL3_DONE $(date -u +%T)"
cd $H && python3 campaign_ablate.py ablate_ini.json
for L in ini5_ctrl ini5_env ini5_keys; do printf "%-10s sps=%s proofs=%s\n" $L "$(python3 -c "import json;print(round(json.load(open('runs/$L/result.json')).get('sps',0)))")" "$(grep -c BATCH_PROOF runs/$L/run.log)"; done
if cmp -s <(grep BATCH_PROOF runs/ini5_env/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/ini5_keys/run.log | sed 's/epoch=[0-9]* //'); then echo "PROOF env-vars vs ini-keys: IDENTICAL"; else echo "PROOF env-vars vs ini-keys: DIFFER"; diff <(grep BATCH_PROOF runs/ini5_env/run.log) <(grep BATCH_PROOF runs/ini5_keys/run.log) | head -4; fi
echo CHAIN_VALIDATE_DONE
