#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; cd $H
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 campaign_ablate.py ablate_shapes.json
for L in a8k5m_coh:8192 a8k15m_coh:8192 mb32k5m_2k:2048 mb32k15m_2k:2048 mb32k15m_4k:4096; do IFS=: read NAME AG <<<"$L"; printf "%-12s " $NAME; python3 sps_from_log.py runs/$NAME/run.log $AG 2>&1 | tail -1; grep -h "BATCH_PERF" runs/$NAME/run.log 2>/dev/null | tail -4 | head -1 | grep -o "seconds=[0-9.]* rollout_tail=[0-9.]* ppo_tail=[0-9.]*\|used_mib=[0-9.]*" | tr '\n' ' '; echo; done
echo CHAIN_SHAPES_DONE
