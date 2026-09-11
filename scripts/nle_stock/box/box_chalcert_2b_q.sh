#!/bin/bash
# Challenge-config cert of the 2B claim weights, QUEUED: each lane is certed as
# soon as its training lane writes a DONE line to long.log, so reads land
# incrementally instead of waiting on the slowest lane. s504 already exited
# (early, at 1.57B) so it starts immediately on its idle GPU.
T=/workspace/PufferLib_pkg
C=/workspace/sweeps/certq/chal2b
L=/workspace/sweeps/certq/chalcert2b.log
TL=/workspace/sweeps/nh/long.log
OPTS=$(grep -m1 "^OPTS=" /workspace/sweeps/certq/box_chalcert_2b.sh | sed "s/^OPTS=.//;s/.$//")
mkdir -p $C; cd $T
ulimit -n 65536
arm() { # gpu seed lane
  gpu=$1; seed=$2; lane=$3; id=chal2b_${lane}
  W=$(ls -1 /workspace/sweeps/nh/checkpoints/nethack/${lane}/*.bin | tail -1)
  steps=$(basename $W .bin | sed "s/^0*//")
  echo "$(date +%T) gpu$gpu START $id weights=$(basename $W) trained_steps=$steps binary=$(md5sum $T/puffer_nethack_stock | cut -c1-12)" >> $L
  NH_STOCK_STRICT=1 NH_STOCK_LITERALOPTS="$OPTS" \
  NH_STOCK_NOSDESC=1 NH_STOCK_NOREDRAW=1 NH_STOCK_STOCKSORT=1 \
  NH_STOCK_NODARKFIX=1 NH_STOCK_NOTOPL=1 NH_STOCK_REALCLOCK=1 \
  NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 \
  NETHACKDIR=/workspace/nle-stock/build/nethackdir \
  NLE_STOCK_LIB=/workspace/nle-stock/build/libnethack.so \
  NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    timeout 86400 ./puffer_nethack_stock eval --headless --base.load_model_path=$W \
      --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 \
      --base.eval_episodes=10000 --base.seed=$seed > $C/$id.out 2> $C/$id.err
  echo "$(date +%T) gpu$gpu DONE $id rc=$? trained_steps=$steps eps=$(wc -l < $C/$id.ep)" >> $L
}
waitlane() { # lane -- block until training lane reports done
  while ! grep -qa "${1} rc=" $TL; do sleep 60; done
  echo "$(date +%T) queue: ${1} training finished, certing" >> $L
}
( arm 5 44 claim2b_s504 ) &
( waitlane claim2b_s501; arm 1 41 claim2b_s501 ) &
( waitlane claim2b_s502; arm 2 42 claim2b_s502 ) &
( waitlane claim2b_s503; arm 3 43 claim2b_s503 ) &
wait
echo "$(date +%T) CHAL2B_DONE" >> $L
