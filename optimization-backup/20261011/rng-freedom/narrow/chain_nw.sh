#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_nw.json > $P/narrow/campaign_nw.log 2>&1
for A in ctrl_a nw16 nw32 nw64 nw128 ctrl_b; do printf "%-10s " nw_$A; python3 sps_from_log.py runs/nw_$A/run.log 2048 2>&1 | tail -1; grep -h -o 'BATCH_PERF epoch=42 seconds=[0-9.]* rollout_tail=[0-9.]* ppo_tail=[0-9.]*' runs/nw_$A/run.log | tail -1 | sed 's/^/    /'; done
for A in nw16 nw32 nw64 nw128 ctrl_b; do cmp -s <(grep BATCH_PROOF runs/nw_ctrl_a/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/nw_$A/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF $A == ctrl" || echo "PROOF $A != ctrl"; done
echo "NW_2048_DONE $(date -u +%T)"
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 campaign_ablate.py ablate_nwc.json > $P/narrow/campaign_nwc.log 2>&1
for A in ctrl_a nw32 nw64 ctrl_b; do printf "%-10s " nwc_$A; python3 sps_from_log.py runs/nwc_$A/run.log 512 512 2>&1 | tail -1; grep -h -o 'BATCH_PERF epoch=4[0-2] seconds=[0-9.]* rollout_tail=[0-9.]* ppo_tail=[0-9.]*' runs/nwc_$A/run.log | tail -1 | sed 's/^/    /'; done
for A in nw32 nw64 ctrl_b; do cmp -s <(grep BATCH_PROOF runs/nwc_ctrl_a/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/nwc_$A/run.log | sed 's/epoch=[0-9]* //') && echo "PROOFC $A == ctrl" || echo "PROOFC $A != ctrl"; done
echo "CHAIN_NW_DONE $(date -u +%T)"
