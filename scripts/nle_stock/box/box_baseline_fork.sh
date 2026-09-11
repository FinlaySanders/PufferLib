#!/bin/bash
# Rung-1 BASELINE: fork-interface cert of the finished claim-config 1B weights ON THE TREE THAT TRAINED THEM
# (PufferLib_pkg, lib bdb9896bd881), same options as training (NH_NLE_OPTS=1), standard protocol
# (512 agents, 14000 eps, per-episode log, burn-in 4000 + next 10000). rc captured BEFORE the echo.
T=/workspace/PufferLib_pkg; C=/workspace/sweeps/certq/base; L=/workspace/sweeps/certq/baseline.log
mkdir -p $C; cd $T; ulimit -n 65536
arm() { gpu=$1; seed=$2; lane=$3; id=fork_${lane}_s${seed}
  W=$(ls -1 /workspace/sweeps/nh/checkpoints/nethack/$lane/*.bin | sort | tail -1)
  echo "$(date +%T) gpu$gpu START $id weights=$(basename $W) wmd5=$(md5sum $W | cut -c1-12) lib=$(md5sum $T/vendor/fast-nle/build/libnethack.so | cut -c1-12) puffer=$(md5sum $T/puffer | cut -c1-12) NH_NLE_OPTS=1" >> $L
  rm -f $C/$id.ep
  NH_NLE_OPTS=1 NETHACKDIR=$T/vendor/fast-nle/build/dat NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    timeout 14400 ./puffer eval --headless --base.load_model_path=$W --policy.hidden_size=1024 --policy.num_layers=4 \
    --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=$seed > $C/$id.out 2> $C/$id.err
  rc=$?
  echo "$(date +%T) gpu$gpu DONE $id rc=$rc nleopts_marker=$(grep -ac "NH_NLE_OPTS active" $C/$id.err) $(python3 /workspace/sweeps/certq/analyze.py $C/$id.ep 2>&1 | tail -1 | cut -c1-170)" >> $L
}
arm 0 7 pkgnle_s406 &
arm 4 11 pkgnle_s406 &
arm 6 7 pkgnle_s407 &
arm 7 11 pkgnle_s407 &
wait; echo "$(date +%T) BASELINE_DONE" >> $L
