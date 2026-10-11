#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; cd $H
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 campaign_ablate.py ablate_knobs4k.json
for L in k4k_ctrl24 k4k_sleep k4k_pin k4k_sleep_pin k4k_w26_sleep; do printf "%-14s " $L; python3 sps_from_log.py runs/$L/run.log 4096 2>&1 | tail -1; done
for L in k4k_sleep k4k_pin k4k_sleep_pin k4k_w26_sleep; do cmp -s <(grep BATCH_PROOF runs/k4k_ctrl24/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/$L/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF $L: identical" || echo "PROOF $L: DIFFERS"; done
echo CHAIN_KNOBS4K_DONE
