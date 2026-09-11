#!/bin/bash
# 4B lanes on the one tree (/workspace/pufferlib, branch nle-stock, engine per ENGINE.txt): the claim
# configuration (sweep_1788766770910_1122.ini via trial_args.py) + NLE default options, 4 seeds.
# Each lane waits for its GPU to be idle, logs the git SHAs and binary md5s it trains on, and captures
# rc on its own line (the old drivers' `echo "... rc=$?"` after $(date) always printed 0).
#
#   T=/workspace/pufferlib LANES="5:601 3:602 2:603 1:604" STEPS=4000000000 bash box_4b.sh
T=${T:-/workspace/pufferlib}; L=${L:-/workspace/sweeps/nh/long.log}; W=${W:-/workspace/sweeps/nh}
LANES=${LANES:-"5:601 3:602 2:603 1:604"}; STEPS=${STEPS:-4000000000}; TAG=${TAG:-nlestock4b}
cd $W; ulimit -n 65536
ARGS=$(python3 $T/scripts/nle_stock/box/trial_args.py $T/scripts/nle_stock/box/sweep_1788766770910_1122.ini)
SHA="pufferlib=$(git -C $T rev-parse --short HEAD)+$(git -C $T status --porcelain | grep -c '^ M')dirty engine=$(git -C $T/vendor/fast-nle rev-parse --short HEAD)+$(git -C $T/vendor/fast-nle status --porcelain | grep -c '^ M')dirty lib=$(md5sum $T/vendor/fast-nle/build/libnethack.so | cut -c1-12) puffer=$(md5sum $T/puffer | cut -c1-12)"
idle() { nvidia-smi --query-gpu=index,memory.used --format=csv,noheader | awk -F, -v g=$1 '$1==g && $2+0<100{f=1} END{exit !f}'; }
lane() { gpu=$1; seed=$2; id=${TAG}_s$seed
  until idle $gpu; do sleep 60; done
  echo "$(date +%T) gpu$gpu START $id ${STEPS} steps CLAIM-CONFIG NH_NLE_OPTS=1 $SHA" >> $L
  NH_NLE_OPTS=1 NETHACKDIR=$T/vendor/fast-nle/build/dat CUDA_VISIBLE_DEVICES=$gpu timeout 259200 $T/puffer train $ARGS \
    --train.total_timesteps=$STEPS --base.seed=$seed --base.run_id=$id > panel_$id.out 2> panel_$id.err
  rc=$?
  echo "$(date +%T) gpu$gpu DONE $id rc=$rc last_ckpt=$(ls -1 checkpoints/nethack/$id/*.bin 2>/dev/null | sort | tail -1 | xargs -r basename) segv=$(grep -c 'Segmentation' panel_$id.err) panel_final=$(tr '\r' '\n' < panel_$id.out | grep -a -oE 'score +[0-9]+\.[0-9]+' | tail -1 | tr -s ' ')" >> $L
}
for gs in $LANES; do lane ${gs%%:*} ${gs##*:} & done
wait; echo "$(date +%T) ${TAG}_DONE" >> $L
