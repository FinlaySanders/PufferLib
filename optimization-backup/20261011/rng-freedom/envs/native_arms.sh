#!/bin/bash
# native shape as control; cohort variants keep agents/horizon/minibatch, change only buffer cut + active set
P=/puffertank/experiments/nethack-rng-freedom-20261011/envs; T=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort/source; H=/puffertank/experiments/nethack-24h-20261009; cd $T
run() { # env arm A Hz nbatches buffers extra
  e=$1; arm=$2; A=$3; Hz=$4; NB=$5; B=$6; X=$7; TS=$((A*Hz*NB)); WARM=$((A*Hz*(NB/3))); G=""; [ $e = craftax ] && G="--train.gpus=1"
  while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
  PUF_POOL_WORKERS=24 PUF_CPU_AFFINITY=1 PUF_PERF_LOADED_PROOF=$P/n_${e}_${arm}.loaded.bin timeout 900 ./puffer_$e train --headless --base.env_name=$e $G --vec.num_buffers=$B $X --train.total_timesteps=$TS --base.seed=901 --base.eval_episodes=0 --base.checkpoint_interval=0 > $P/n_${e}_${arm}.log 2>&1
  printf "%-9s %-9s buffers=%-3s rc=%s  " $e $arm $B $? ; python3 $H/sps_from_log.py $P/n_${e}_${arm}.log $A $Hz $WARM 2>&1 | tail -1
}
# breakout native: 4096 agents, 1 buffer, horizon 32
run breakout native_a 4096 32 96 1 ""
run breakout c128     4096 32 96 32 "--vec.cohort_buffers=4 --vec.cohort_steps=32"
run breakout chalf    4096 32 96 2  "--vec.cohort_buffers=1 --vec.cohort_steps=32"
run breakout cquarter 4096 32 96 4  "--vec.cohort_buffers=1 --vec.cohort_steps=32"
run breakout native_b 4096 32 96 1 ""
# drone native: 8192 agents, 8 buffers, horizon 64
run drone native_a 8192 64 96 8 ""
run drone c128     8192 64 96 64 "--vec.cohort_buffers=4 --vec.cohort_steps=64"
run drone chalf    8192 64 96 16 "--vec.cohort_buffers=8 --vec.cohort_steps=64"
run drone cquarter 8192 64 96 32 "--vec.cohort_buffers=8 --vec.cohort_steps=64"
run drone native_b 8192 64 96 8 ""
# craftax native: 2048 agents, 4 buffers, horizon 256 (c128 == cquarter here)
run craftax native_a 2048 256 32 4 ""
run craftax c128     2048 256 32 16 "--vec.cohort_buffers=4 --vec.cohort_steps=64"
run craftax chalf    2048 256 32 8  "--vec.cohort_buffers=4 --vec.cohort_steps=64"
run craftax native_b 2048 256 32 4 ""
echo "NATIVE_ARMS_DONE $(date -u +%T)"
