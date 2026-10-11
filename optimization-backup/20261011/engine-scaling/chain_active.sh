#!/bin/bash
# PUF_COHORT_ACTIVE screen: build cohort_act, run act_ctrl/act1/act2/act3 (5M/2048, 16x128 g4 s64 via ini keys), sample act2, compare proofs
R=/puffertank/experiments/nethack-engine-scaling-20261010; T=$R/trainer_cohort; H=/puffertank/experiments/nethack-24h-20261009
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $T && rm -rf snapshots/cohort_act && python3 build.py cohort_act -DPUF_MUON_OUTPLACE -lcuda > $T/build_cohort_act.out 2>&1; rc=$?; echo "BUILD_cohort_act rc=$rc $(date -u +%T)"
[ $rc -eq 0 ] || { grep -m5 "error" $T/cohort_act-build.log | cut -c1-200; echo CHAIN_ABORT_BUILD; exit 1; }
ln -sfn $T/binaries/cohort_act $H/binaries/cohort_act
cd $H && python3 campaign_ablate.py ablate_active.json &
NAME=act2
while ! PID=$(pgrep -f "^/puffertank/experiments/nethack-24h-20261009/binaries/cohort_act .*" | head -1) || [ -z "$PID" ] || ! grep -q "$NAME" /proc/$PID/cmdline 2>/dev/null; do sleep 1; done
echo "ATTACH $NAME pid=$PID $(date -u +%T)"; cd $H && ./thread_util.sh $PID 12 28 | sed "s/^/$NAME: /"
wait
cd $H && for L in act_ctrl act1 act2 act3; do printf "%-9s sps=%s\n" $L "$(python3 -c "import json;print(round(json.load(open('runs/$L/result.json')).get('sps',0)))")"; done
for L in act1 act2 act3; do cmp -s <(grep BATCH_PROOF runs/act_ctrl/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/$L/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF $L: identical to act_ctrl" || echo "PROOF $L: DIFFERS"; done
echo CHAIN_ACTIVE_DONE
