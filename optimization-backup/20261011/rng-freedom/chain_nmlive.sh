#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_nmlive.json > $P/campaign_nmlive.log 2>&1
for T in nmlive_5m2k:2048 nmlive_5m4k:4096; do IFS=: read TAG AG <<<"$T"; for A in ctrl_a cand_a cand_b ctrl_b; do printf "%-22s " ${TAG}_$A; python3 sps_from_log.py runs/${TAG}_$A/run.log $AG 2>&1 | tail -1; done; done
cmp -s <(grep BATCH_PROOF runs/nmlive_5m2k_ctrl_a/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/nmlive_5m2k_cand_a/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF cand==ctrl (masks NOT applied)" || echo "PROOF cand!=ctrl (live + masks applied)"
grep -h -o 'BATCH_PERF.*' runs/nmlive_5m2k_ctrl_b/run.log | tail -2 | sed 's/^/CTRL_PERF /'; grep -h -o 'BATCH_PERF.*' runs/nmlive_5m2k_cand_b/run.log | tail -2 | sed 's/^/CAND_PERF /'
echo "CHAIN_NMLIVE_DONE $(date -u +%T)"
