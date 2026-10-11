#!/bin/bash
# batch-scaling check: 4096 agents, cohort (32x128 g4 s64, 24 workers) vs control (4x1024, 32 workers), 5M and 15M
H=/puffertank/experiments/nethack-24h-20261009; cd $H
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 campaign_ablate.py ablate_4096.json
for L in a4k5m_ctrl a4k5m_coh a4k15m_ctrl a4k15m_coh; do printf "%-12s sps=%s\n" $L "$(python3 -c "import json;print(round(json.load(open('runs/$L/result.json')).get('sps',0)))")"; done
echo CHAIN_4096_DONE
