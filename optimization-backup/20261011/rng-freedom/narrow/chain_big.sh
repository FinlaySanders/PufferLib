#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011
while ! grep -q CHAIN_NW_DONE $P/narrow/chain_nw.log; do sleep 10; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_big.json > $P/narrow/campaign_big.log 2>&1
for A in ctrl_a b4c2s64 b4c2s128 b8c4s64 b8c4s128 b4plain ctrl_b; do printf "%-12s " big_$A; python3 sps_from_log.py runs/big_$A/run.log 2048 2>&1 | tail -1; grep -h -o 'BATCH_PERF epoch=42 seconds=[0-9.]* rollout_tail=[0-9.]* ppo_tail=[0-9.]*' runs/big_$A/run.log | tail -1 | sed 's/^/    /'; done
echo "CHAIN_BIG_DONE $(date -u +%T)"
