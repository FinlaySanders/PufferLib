#!/bin/bash
# Rung-1 BASELINE for the 2B claim lanes: fork-interface cert on the pkg tree, fires per lane once
# (a) the 1B baseline arms have released gpus 0/4/6/7 and (b) that lane has written its DONE line.
# gpus 1/2/3/5 belong to box_chalcert_2b_q.sh (rung-3) -- do not touch them here.
T=/workspace/PufferLib_pkg; C=/workspace/sweeps/certq/base; L=/workspace/sweeps/certq/baseline.log; TL=/workspace/sweeps/nh/long.log
mkdir -p $C; cd $T; ulimit -n 65536
arm() { gpu=$1; seed=$2; lane=$3; id=fork_${lane}_s${seed}
  W=$(ls -1 /workspace/sweeps/nh/checkpoints/nethack/$lane/*.bin | sort | tail -1); steps=$(basename $W .bin | sed "s/^0*//")
  echo "$(date +%T) gpu$gpu START $id weights=$(basename $W) trained_steps=$steps wmd5=$(md5sum $W | cut -c1-12) lib=$(md5sum $T/vendor/fast-nle/build/libnethack.so | cut -c1-12) puffer=$(md5sum $T/puffer | cut -c1-12) NH_NLE_OPTS=1" >> $L
  rm -f $C/$id.ep
  NH_NLE_OPTS=1 NETHACKDIR=$T/vendor/fast-nle/build/dat NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    timeout 14400 ./puffer eval --headless --base.load_model_path=$W --policy.hidden_size=1024 --policy.num_layers=4 \
    --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=$seed > $C/$id.out 2> $C/$id.err
  rc=$?
  echo "$(date +%T) gpu$gpu DONE $id rc=$rc trained_steps=$steps nleopts_marker=$(grep -ac "NH_NLE_OPTS active" $C/$id.err) $(python3 /workspace/sweeps/certq/analyze.py $C/$id.ep 2>&1 | tail -1 | cut -c1-170)" >> $L
}
until grep -qa BASELINE_DONE $L; do sleep 60; done
waitlane() { until grep -qa "${1} rc=" $TL; do sleep 60; done; echo "$(date +%T) queue2b: ${1} training finished" >> $L; }
( waitlane claim2b_s503; arm 0 7 claim2b_s503 ) &
( waitlane claim2b_s503; arm 7 11 claim2b_s503 ) &
( waitlane claim2b_s502; arm 4 7 claim2b_s502 ) &
( waitlane claim2b_s501; arm 6 7 claim2b_s501 ) &
wait; echo "$(date +%T) BASELINE2B_DONE" >> $L
