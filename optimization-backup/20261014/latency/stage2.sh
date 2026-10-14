#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/stage2.log; echo "stage2 start $(date -u +%T)" > $G
rm -f $L/ab_mock.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_mock.json > $L/ab_mock.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
for lab in mock_real_cap12 mock_k67_adapt mock_k20_adapt mock_k10_adapt mock_k4_adapt mock_k1_adapt mock_k10_cap4 mock_real_cap12_b; do
  r=/puffertank/experiments/nethack-24h-20261009/runs/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_mock.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'borrow_pct=[^ ]+|cap_mean=[^ ]+|rt_us=[^ ]+|step_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+|idle_mean=[^ ]+' | tr '\n' ' ') | $(grep SCHED_CORES $r | tail -1 | grep -oE 'P_us_per_step=[^ ]+|E_us_per_step=[^ ]+' | tr '\n' ' ')" >> $G
done
echo "STAGE2_DONE $(date -u +%T)" >> $G
