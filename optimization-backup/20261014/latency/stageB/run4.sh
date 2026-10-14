#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/stageB/run4.log; echo "stageE start $(date -u +%T)" > $G
rm -f $L/ab_stageE.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_stageE.json > $L/ab_stageE.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
R=/puffertank/experiments/nethack-24h-20261009/runs
for lab in sE_off sE_AB0 sE_AB0_nosplit sE_AB0_nosplit_adapt sE_nosplit_only sE_off_b; do
  r=$R/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_stageE.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'cap_mean=[^ ]+|rt_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+|borrow_pct=[^ ]+' | tr '\n' ' ') | $(grep SCHED_GRAPH $r | head -1) | plans: $(grep -c 'NH_FUSED_PLAN' $r)" >> $G
done
echo "STAGEE_DONE $(date -u +%T)" >> $G
