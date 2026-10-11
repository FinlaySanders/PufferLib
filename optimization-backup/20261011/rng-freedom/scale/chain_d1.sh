#!/bin/bash
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py ablate_d1.json > /puffertank/experiments/nethack-rng-freedom-20261011/scale/campaign_d1.log 2>&1
for A in 15m_ctrl 15m_b4c1s64 15m_b4c1s128 5m_ctrl 5m_b4c1s64 15m_ctrl_b; do printf "%-16s " d1_$A; python3 sps_from_log.py runs/d1_$A/run.log 2048 2>&1 | tail -1 | cut -c1-12; grep -h -o 'BATCH_PERF epoch=42 seconds=[0-9.]* rollout_tail=[0-9.]* ppo_tail=[0-9.]*' runs/d1_$A/run.log | tail -1 | sed 's/^/    /'; done
echo "CHAIN_D1_DONE $(date -u +%T)"
