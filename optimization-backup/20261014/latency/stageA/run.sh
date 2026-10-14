#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/stageA/run.log; echo "stageA start $(date -u +%T)" > $G
rm -f $L/ab_stageA.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_stageA.json > $L/ab_stageA.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
R=/puffertank/experiments/nethack-24h-20261009/runs
python3 - >> $G <<'PY'
import hashlib
R='/puffertank/experiments/nethack-24h-20261009/runs'
for lab in ['sA_live_off','sA_live_on']:
    try: t=open(f'{R}/{lab}/run.log',errors='replace').read()
    except FileNotFoundError: print(lab,'missing'); continue
    lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
    g=[l for l in t.splitlines() if l.startswith('SCHED_GRAPH')]
    print(lab, len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '| graph:', g[:1])
PY
for lab in sA_fast_off sA_fast_on sA_fast_on_adapt sA_fast_off_b; do
  r=$R/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_stageA.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'cap_mean=[^ ]+|rt_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+' | tr '\n' ' ') | $(grep BATCH_PROOF $r | tail -1 | grep -oE 'obs=[0-9a-f]+')" >> $G
done
echo "STAGEA_DONE $(date -u +%T)" >> $G
