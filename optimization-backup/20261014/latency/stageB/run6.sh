#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/stageB/run6.log; echo "stageG start $(date -u +%T)" > $G
rm -f $L/ab_stageG.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_stageG.json > $L/ab_stageG.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
R=/puffertank/experiments/nethack-24h-20261009/runs
for lab in sG_off sG_AB0 sG_AB0S sG_AB0S_adapt sG_AB0S_cap8 sG_AB0S_cap8_w150 sG_AB0S_cap6_b300 sG_off_b; do
  r=$R/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_stageG.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'cap_mean=[^ ]+|rt_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+|borrow_pct=[^ ]+|idle_mean=[^ ]+' | tr '\n' ' ') | $(grep SCHED_CORES $r | tail -1 | grep -oE 'P_us_per_step=[^ ]+|E_us_per_step=[^ ]+' | tr '\n' ' ')" >> $G
done
python3 - >> $G <<'PY'
import hashlib
R='/puffertank/experiments/nethack-24h-20261009/runs'
t=open(f'{R}/sG_live_AB0S/run.log',errors='replace').read(); lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
print('sG_live_AB0S', len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '(exact target 31e2e3deae720ef4)')
PY
echo "STAGEG_DONE $(date -u +%T)" >> $G
