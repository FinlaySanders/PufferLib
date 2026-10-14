#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/stage3.log; echo "stage3 start $(date -u +%T)" > $G
rm -f $L/ab_pop.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_pop.json > $L/ab_pop.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
for lab in pop_pool_4096 pop_sched_4096 pop_mock4_4096 pop_pool_8192 pop_sched_8192 pop_mock4_8192; do
  r=/puffertank/experiments/nethack-24h-20261009/runs/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_pop.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'borrow_pct=[^ ]+|cap_mean=[^ ]+|rt_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+' | tr '\n' ' ') | $(grep SCHED_CORES $r | tail -1 | grep -oE 'P_us_per_step=[^ ]+|E_us_per_step=[^ ]+' | tr '\n' ' ')" >> $G
done
echo "STAGE3_DONE $(date -u +%T)" >> $G
