#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011
while ! grep -q 'CHAIN_RC2_DONE' $P/chain_rc2.log; do sleep 10; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_nomacro.json > $P/campaign_nomacro.log 2>&1
for T in nomacro_5m2k:2048 nomacro_5m4k:4096; do IFS=: read TAG AG <<<"$T"; for A in ctrl_a cand_a cand_b ctrl_b; do printf "%-22s " ${TAG}_$A; python3 sps_from_log.py runs/${TAG}_$A/run.log $AG 2>&1 | tail -1; done; done
grep -m2 -i 'error\|unknown\|invalid' runs/nomacro_5m2k_cand_a/run.log | sed 's/^/CAND_LOG /' || true
echo "CHAIN_NOMACRO_DONE $(date -u +%T)"
