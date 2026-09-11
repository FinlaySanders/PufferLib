#!/bin/bash
# Retire the two duplicate real-clock arms and relaunch them with distinct env seeds.
# chal_s21_real (gpu0) and chal_s24_fake (gpu7) keep running: with no seed argument they
# play the identical game sequence, which makes them a perfectly controlled
# faked-clock vs real-clock comparison. The new arms supply independent samples.
T=/workspace/PufferLib_pkg
C=/workspace/sweeps/certq/chal
L=/workspace/sweeps/certq/chalcert.log
W=/workspace/sweeps/nh/checkpoints/nethack/pkgnle_s406/0000000999817216.bin
OPTS='autopickup,color,disclose:+i +a +v +g +c +o,mention_walls,nobones,nocmdassist,nolegacy,nosparkle,pickup_burden:unencumbered,pickup_types:$?!/,runmode:teleport,showexp,showscore,time,name:Agent-@,race:random,gender:random,align:random'
cd $T; ulimit -n 65536
for p in 534715 534716; do kill $p 2>/dev/null; done
sleep 5
for p in 534718 534720; do kill $p 2>/dev/null; done
sleep 3
echo "$(date +%T) retired duplicate arms chal_s22_real chal_s23_real (no --base.seed: identical games)" >> $L
arm() {
  gpu=$1; seed=$2; id=chal_s${seed}_real
  echo "$(date +%T) gpu$gpu START $id seed=$seed (independent)" >> $L
  NH_STOCK_STRICT=1 NH_STOCK_LITERALOPTS="$OPTS" NH_STOCK_NOSDESC=1 NH_STOCK_NOREDRAW=1 \
  NH_STOCK_STOCKSORT=1 NH_STOCK_NODARKFIX=1 NH_STOCK_NOTOPL=1 NH_STOCK_REALCLOCK=1 \
  NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 \
  NETHACKDIR=/workspace/nle-stock/build/nethackdir NLE_STOCK_LIB=/workspace/nle-stock/build/libnethack.so \
  NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    timeout 86400 ./puffer_nethack_stock eval --headless --base.load_model_path=$W \
      --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 \
      --base.eval_episodes=10000 --base.seed=$seed > $C/$id.out 2> $C/$id.err
  echo "$(date +%T) gpu$gpu DONE $id rc=$? eps=$(wc -l < $C/$id.ep)" >> $L
}
arm 4 32 &
arm 6 33 &
wait
