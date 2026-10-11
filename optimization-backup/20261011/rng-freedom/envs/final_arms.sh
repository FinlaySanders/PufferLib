#!/bin/bash
P=/puffertank/experiments/nethack-rng-freedom-20261011/envs; T=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort/source; H=/puffertank/experiments/nethack-24h-20261009; cd $T
run() { # env arm buffers extra
  e=$1; arm=$2; B=$3; X=$4; A=2048; TS=$((A*128*32)); WARM=$((A*128*12)); G=""; [ $e = craftax ] && G="--train.gpus=1"
  while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
  PUF_POOL_WORKERS=24 PUF_CPU_AFFINITY=1 PUF_PERF_LOADED_PROOF=$P/${e}_${arm}.loaded.bin timeout 900 ./puffer_$e train --headless --base.env_name=$e $G --vec.total_agents=$A --train.horizon=128 --vec.num_buffers=$B $X --train.total_timesteps=$TS --base.seed=901 --base.eval_episodes=0 --base.checkpoint_interval=0 > $P/${e}_${arm}.log 2>&1
  printf "%-9s %-8s rc=%s  " $e $arm $? ; python3 $H/sps_from_log.py $P/${e}_${arm}.log $A 128 $WARM 2>&1 | tail -1
}
C="--vec.cohort_buffers=4 --vec.cohort_steps=64"
run craftax ctrl_a 4 ""; run craftax coh_a 16 "$C"; run craftax coh_b 16 "$C"; run craftax ctrl_b 4 ""; run craftax b16nocoh 16 ""
run breakout b16nocoh 16 ""; run drone b16nocoh 16 ""
echo "FINAL_ARMS_DONE $(date -u +%T)"
