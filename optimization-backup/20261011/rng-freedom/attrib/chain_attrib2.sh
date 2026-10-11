#!/bin/bash
while ! grep -q CHAIN_ATTRIB_DONE /puffertank/experiments/nethack-rng-freedom-20261011/attrib/chain_attrib.log; do sleep 15; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py ablate_attrib2.json > /puffertank/experiments/nethack-rng-freedom-20261011/attrib/campaign_attrib2.log 2>&1
for A in M1_engine M2_sched M3_gpukernels M4_lanes4 M5_gradoverlap ctrl_b; do printf "%-24s " att2_15m2k_$A; python3 sps_from_log.py runs/att2_15m2k_$A/run.log 2048 2>&1 | tail -1 | cut -c1-40; done
echo "CHAIN_ATTRIB2_DONE $(date -u +%T)"
