#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; R=/puffertank/experiments/nethack-engine-scaling-20261010; T=$R/trainer_cohort; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q "CHAIN_DEPTH8_DONE\|CHAIN_ABORT" $S/chain_depth8.log; do sleep 5; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $T && rm -rf snapshots/cohort_pin2 && python3 build.py cohort_pin2 -DPUF_MUON_OUTPLACE -lcuda > $T/build_cohort_pin2.out 2>&1; rc=$?; echo "BUILD_cohort_pin2 rc=$rc $(date -u +%T)"
[ $rc -eq 0 ] || { grep -m5 "error" $T/cohort_pin2-build.log | cut -c1-200; echo CHAIN_ABORT_BUILD; exit 1; }
ln -sfn $T/binaries/cohort_pin2 $H/binaries/cohort_pin2
cd $H && python3 campaign_ablate.py ablate_split.json
for L in split24_pin split24_pin_sleep; do echo "== $L $(python3 sps_from_log.py runs/$L/run.log 4096 2>&1 | tail -1)"; python3 pool_worker_split.py runs/$L/run.log | tail -1; done
echo CHAIN_SPLIT_DONE
