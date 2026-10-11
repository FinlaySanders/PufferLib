#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_fx2.json > $P/fx/campaign_fx2.log 2>&1
for A in ctrl_a wide50 mid50 wide20 ctrl_b; do printf "%-12s " fx2_$A; python3 sps_from_log.py runs/fx2_$A/run.log 2048 2>&1 | tail -1; grep -h -o 'BATCH_PERF epoch=42 seconds=[0-9.]* rollout_tail=[0-9.]* ppo_tail=[0-9.]*' runs/fx2_$A/run.log | tail -1 | sed 's/^/    /'; done
echo "CHAIN_FX2_DONE $(date -u +%T)"
