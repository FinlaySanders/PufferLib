#!/bin/bash
# regime grid for kernel v1.4 (PGO engine): 5M x {4096, 8192} on scheduler and pool trainers, 15M x {2048, 4096} on the scheduler, off/on, 2 reps
P=/puffertank/experiments/nethack-monster-turn-plan-20261014; L=$P/stage_k13.log
echo "stage K13 waiting for K12 $(date -u +%T)" > $L
while ! grep -q STAGEK12_DONE $P/stage_k12.log 2>/dev/null; do sleep 15; done
rm -f $P/ab_mt2v14_grid.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $P/ab_mt2v14_grid.json > $P/ab_mt2v14_grid.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $L)
python3 - >> $L <<'PY'
import json
P='/puffertank/experiments/nethack-monster-turn-plan-20261014'
r={x['label']:x['sps'] for x in json.load(open(f'{P}/ab_mt2v14_grid.results.json'))}
for rk in ('5m4k','5m8k','15m2k','15m4k'):
    for b in ('v22','v12'):
        off=[r.get(f'g_{rk}_{b}_off_{k}') for k in 'ab']; on=[r.get(f'g_{rk}_{b}_on_{k}') for k in 'ab']
        off=[x for x in off if x]; on=[x for x in on if x]
        if off and on: print(f"{rk:6s} {b}: off {'/'.join(f'{x:.0f}' for x in off)}  on {'/'.join(f'{x:.0f}' for x in on)}  +{100*(sum(on)/len(on)/(sum(off)/len(off))-1):.1f}%")
PY
echo "STAGEK13_DONE $(date -u +%T)" >> $L
