#!/bin/bash
# Pool-timing anatomy of the recommended cohort config; starts after the mt8 census so the clock is clean.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
while ! grep -q "CHAIN_mt8_DONE\|CHAIN_ABORT" $S/chain_mt8.log; do sleep 20; done; echo "WAIT_MT8_DONE $(date -u +%T)"
cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py ablate_pooltiming.json
for L in pt5_ctrl pt5_b16c4s64 pt15m_b16c4s64 pt15m_ctrl; do echo "== $L"; python3 pool_timing_report.py runs/$L/run.log 64; done
echo CHAIN_POOLTIMING_DONE
