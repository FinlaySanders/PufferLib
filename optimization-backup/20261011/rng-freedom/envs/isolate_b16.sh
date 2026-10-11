#!/bin/bash
# isolate buffer size from cohort: 16 x 128 buffers, all active (no cohort), one run per env
P=/puffertank/experiments/nethack-rng-freedom-20261011/envs; T=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort/source; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q CAMPAIGN_ENVS_DONE $P/campaign_envs.log; do sleep 10; done
declare -A AG=([breakout]=2048 [drone]=2048 [moba]=2560 [chess]=2048 [craftax]=2048)
cd $T
for e in breakout drone moba chess craftax; do A=${AG[$e]}; TS=$((A*128*32)); WARM=$((A*128*12))
  while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
  PUF_POOL_WORKERS=24 PUF_CPU_AFFINITY=1 PUF_PERF_LOADED_PROOF=$P/${e}_b16.loaded.bin timeout 900 ./puffer_$e train --headless --base.env_name=$e --vec.total_agents=$A --train.horizon=128 --vec.num_buffers=16 --train.total_timesteps=$TS --base.seed=901 --base.eval_episodes=0 --base.checkpoint_interval=0 > $P/${e}_b16.log 2>&1
  printf "%-9s b16nocoh rc=%s  " $e $?; python3 $H/sps_from_log.py $P/${e}_b16.log $A 128 $WARM 2>&1 | tail -1
done
echo "ISOLATE_DONE $(date -u +%T)"
