#!/bin/bash
# trainer A/B of the kernel: live-learning digest (NH_MT2=1) + fast-protocol SPS, NH_MT2=0 vs 1, scheduler (v22) and pool (v12) trainers
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; L=$P/stage_k3.log
echo "stage K3 waiting for K2 $(date -u +%T)" > $L
while ! grep -q STAGEK2_DONE $P/stage_k2.log 2>/dev/null; do sleep 15; done
rm -f $P/ab_mt2.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $P/ab_mt2.json > $P/ab_mt2.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $L)
grep -E '^DONE' $P/ab_mt2.log >> $L
python3 - >> $L <<'PY'
import hashlib
t=open('/puffertank/experiments/nethack-24h-20261009/runs/mt2_live_on_v22/run.log',errors='replace').read(); lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
print('mt2_live_on_v22', len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '(exact target 31e2e3deae720ef4)')
PY
echo "STAGEK3_DONE $(date -u +%T)" >> $L
