#!/bin/bash
X=/puffertank/experiments/nethack-scheduler-20261012; H=/puffertank/experiments/nethack-24h-20261009; D=/puffertank/docker/perf_rot
while ! grep -q CONTAINER_ROT_DONE $D/container_rot.log 2>/dev/null; do sleep 15; done
cd $H && for L in cap_ctrl cap8_batch cap10_batch cap12_batch cap14_batch cap12_batch_pw15 cap12_batch_k15 cap_ctrl_b; do rm -rf runs/$L; done
python3 campaign_ablate.py $X/trainer/ab_cap.json 2>&1 | grep DONE
for L in cap8_batch cap10_batch cap12_batch cap14_batch cap12_batch_pw15 cap12_batch_k15; do echo "$L $(grep -E 'SCHED_STATS|SCHED_INFER|SCHED_CORES' $H/runs/$L/run.log | tail -3 | grep -oE 'us_per_step=[0-9.]+|borrow_pct=[0-9.]+|forward_us=[0-9]+|hot_set_mean=[0-9.]+' | tr '\n' ' ')"; done
echo CHAIN_CAP_DONE
