#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; cd $H
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 campaign_ablate.py ablate_landing5.json
for T in land5_5m4k:4096 land5_15m2k:2048; do IFS=: read TAG AG <<<"$T"; for S in ctrl_a cand_a cand_b ctrl_b; do printf "%-20s " ${TAG}_$S; python3 sps_from_log.py runs/${TAG}_$S/run.log $AG 2>&1 | tail -1; done; done
for T in land5_5m4k land5_15m2k; do cmp -s <(grep BATCH_PROOF runs/${T}_ctrl_a/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/${T}_cand_a/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF $T cand vs ctrl: identical" || echo "PROOF $T: DIFFERS"; done
echo CHAIN_LAND5B_DONE
