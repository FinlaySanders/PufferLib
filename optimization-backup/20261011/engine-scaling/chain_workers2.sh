#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q "CHAIN_WORKERS_DONE" $S/chain_workers.log; do sleep 5; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_workers2.json
for L in w16 w20 w22 w24 w26 w28 w36; do printf "%-5s sps=%s\n" $L "$(python3 -c "import json;print(round(json.load(open('runs/$L/result.json')).get('sps',0)))")"; done
for L in w16 w20 w22 w26; do cmp -s <(grep BATCH_PROOF runs/spin_ctrl/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/$L/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF $L: identical" || echo "PROOF $L: DIFFERS"; done
echo CHAIN_WORKERS2_DONE
