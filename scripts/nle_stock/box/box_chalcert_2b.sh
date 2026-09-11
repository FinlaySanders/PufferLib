#!/bin/bash
# Challenge-configuration cert for the 2B claim weights (claim2b_s501..504).
# Identical configuration to box_chalcert.sh -- strict caps, NLE's literal option
# string, no screen descriptions, no redraw hook, stock room ordering, both probe
# crutches off, real clock -- but with --base.seed per arm, which the first
# version omitted (three arms then played identical games).
T=/workspace/PufferLib_pkg
C=/workspace/sweeps/certq/chal2b
L=/workspace/sweeps/certq/chalcert2b.log
OPTS='autopickup,color,disclose:+i +a +v +g +c +o,mention_walls,nobones,nocmdassist,nolegacy,nosparkle,pickup_burden:unencumbered,pickup_types:$?!/,runmode:teleport,showexp,showscore,time,name:Agent-@,race:random,gender:random,align:random'
mkdir -p $C; cd $T
ulimit -n 65536
arm() { # gpu seed lane
  gpu=$1; seed=$2; lane=$3; id=chal2b_${lane}
  W=$(ls -1 /workspace/sweeps/nh/checkpoints/nethack/${lane}/*.bin | tail -1)
  echo "$(date +%T) gpu$gpu START $id weights=$(basename $W) binary=$(md5sum $T/puffer_nethack_stock | cut -c1-12)" >> $L
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
  echo "$(date +%T) gpu$gpu DONE $id rc=$? eps=$(wc -l < $C/$id.ep)" >> $L
}
arm 1 41 claim2b_s501 &
arm 2 42 claim2b_s502 &
arm 3 43 claim2b_s503 &
arm 5 44 claim2b_s504 &
wait
echo "$(date +%T) CHAL2B_DONE" >> $L
