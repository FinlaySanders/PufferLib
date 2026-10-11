#!/bin/bash
C=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort; H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011; S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
while ! grep -q 'binary_sha256\|SystemExit\|error' $S/build_fx.log; do sleep 10; done
[ -f $C/binaries/cohort_fx ] || { echo "BUILD_FX_FAILED"; grep -m3 -i 'error' $S/build_fx.log | cut -c1-200; exit 1; }
ln -sfn $C/binaries/cohort_fx $H/binaries/cohort_fx; echo "FX_BUILT $(date -u +%T)"
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_fx.json > $P/fx/campaign_fx.log 2>&1
for A in ctrl_a cache dummy50 dummy100 burn16 ctrl_b; do printf "%-12s " fx_$A; python3 sps_from_log.py runs/fx_$A/run.log 2048 2>&1 | tail -1; done
for A in cache dummy50 dummy100 burn16 ctrl_b; do cmp -s <(grep BATCH_PROOF runs/fx_ctrl_a/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/fx_$A/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF $A == ctrl" || echo "PROOF $A != ctrl"; done
for A in ctrl_a dummy50 burn16; do grep -h -o 'BATCH_PERF epoch=4[0-2] seconds=[0-9.]* rollout_tail=[0-9.]* ppo_tail=[0-9.]*' runs/fx_$A/run.log | tail -1 | sed "s/^/PERF $A /"; done
echo "CHAIN_FX_DONE $(date -u +%T)"
