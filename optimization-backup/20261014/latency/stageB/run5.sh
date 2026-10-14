#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/stageB/run5.log; echo "stageF start $(date -u +%T)" > $G
rm -f $L/ab_stageF.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_stageF.json > $L/ab_stageF.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
R=/puffertank/experiments/nethack-24h-20261009/runs
for lab in sF_off sF_AB0_cap12 sF_AB0_adapt_b0 sF_AB0_adapt_b100 sF_AB0_adapt_b300 sF_AB0_cap6_b300 sF_AB0_cap6_b1000 sF_off_b; do
  r=$R/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_stageF.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'cap_mean=[^ ]+|rt_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+|borrow_pct=[^ ]+|idle_mean=[^ ]+|busy_mean=[^ ]+' | tr '\n' ' ') | $(grep SCHED_CORES $r | tail -1 | grep -oE 'P_us_per_step=[^ ]+|E_us_per_step=[^ ]+' | tr '\n' ' ')" >> $G
done
echo "STAGEF_DONE $(date -u +%T)" >> $G
