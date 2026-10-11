#!/bin/bash
# build patched trainer (cohort ini keys) -> in-window pool utilisation (util3) -> ini-key validation (3 arms) -> proof comparison
R=/puffertank/experiments/nethack-engine-scaling-20261010; T=$R/trainer_cohort; H=/puffertank/experiments/nethack-24h-20261009
cd $T && python3 build.py cohort_ini > $T/build_cohort_ini.out 2>&1; rc=$?; echo "BUILD_cohort_ini rc=$rc $(date -u +%T)"
[ $rc -eq 0 ] || { tail -30 $T/cohort_ini-build.log; echo CHAIN_ABORT_BUILD; exit 1; }
ln -sfn $T/binaries/cohort_ini $H/binaries/cohort_ini
$R/chain_util3.sh; echo "UTIL3_DONE $(date -u +%T)"
cd $H && python3 campaign_ablate.py ablate_ini.json
for L in ini5_ctrl ini5_env ini5_keys; do printf "%-10s sps=%s proofs=%s\n" $L "$(python3 -c "import json;print(round(json.load(open('runs/$L/result.json')).get('sps',0)))")" "$(grep -c BATCH_PROOF runs/$L/run.log)"; done
if cmp -s <(grep BATCH_PROOF runs/ini5_env/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/ini5_keys/run.log | sed 's/epoch=[0-9]* //'); then echo "PROOF env-vars vs ini-keys: IDENTICAL"; else echo "PROOF env-vars vs ini-keys: DIFFER"; diff <(grep BATCH_PROOF runs/ini5_env/run.log) <(grep BATCH_PROOF runs/ini5_keys/run.log) | head -4; fi
echo CHAIN_VALIDATE_DONE
