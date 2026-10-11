#!/bin/bash
# cohort vs control on other envs: 2048 agents x horizon 128 (batch 262,144), 32 epochs, window epochs 11..30
T=/puffertank/experiments/nethack-engine-scaling-20261010/trainer_cohort/source; S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; P=/puffertank/experiments/nethack-rng-freedom-20261011/envs; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q BUILDS_DONE $S/build_envs.log; do sleep 15; done
cd $T
declare -A AG=([breakout]=2048 [drone]=2048 [moba]=2560 [chess]=2048 [craftax]=2048)
for e in breakout drone moba chess craftax; do A=${AG[$e]}; TS=$((A*128*32)); WARM=$((A*128*12))
  [ -x puffer_$e ] || { echo "SKIP $e (no binary)"; continue; }
  for arm in ctrl_a coh_a coh_b ctrl_b; do
    if [[ $arm == coh* ]]; then B=16; X="--vec.cohort_buffers=4 --vec.cohort_steps=64"; else B=4; X=""; fi
    while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
    PUF_POOL_WORKERS=24 PUF_CPU_AFFINITY=1 PUF_PERF_LOADED_PROOF=$P/${e}_${arm}.loaded.bin timeout 900 ./puffer_$e train --headless --base.env_name=$e --vec.total_agents=$A --train.horizon=128 --vec.num_buffers=$B $X --train.total_timesteps=$TS --base.seed=901 --base.eval_episodes=0 --base.checkpoint_interval=0 > $P/${e}_${arm}.log 2>&1
    rc=$?
    printf "%-9s %-7s rc=%s  " $e $arm $rc; python3 $H/sps_from_log.py $P/${e}_${arm}.log $A 128 $WARM 2>&1 | tail -1
    [ $rc -ne 0 ] && grep -m1 -i 'error\|assert\|missing\|segmentation\|abort' $P/${e}_${arm}.log | cut -c1-160
  done
done
echo "CAMPAIGN_ENVS_DONE $(date -u +%T)"
