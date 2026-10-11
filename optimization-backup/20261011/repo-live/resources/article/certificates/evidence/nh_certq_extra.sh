#!/bin/bash
# Extra cert workers for GPUs 4 and 6 (free once the two no-mask 4B lanes finish ~03:05/03:30). First: own-engine fork certs of the no-mask lanes with
# NH_NO_CANT_HOLD=1 (the mask they trained without), 14000 eps seed 7 = the A/B against the masked leaky 4B forkleaky certs. Then: generic workers on the
# shared queue of nh_certq_fix.sh (same job format, same flock), so the 2B/4B certs finish sooner. Never resets the queue file.
F=/workspace/pufferlib_fix; W=/workspace/pufferlib; C=/workspace/sweeps/certq/equiv; L=$C/equiv.log; Q=/workspace/sweeps/nhfix/certq_fix; ulimit -n 65536
gpu_idle() { [ -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader --id=$1 2>/dev/null)" ]; }
STOCKENV="NH_STOCK_STRICT=1 NH_STOCK_LITERALOPTS= NH_STOCK_NOSDESC=1 NH_STOCK_NOREDRAW=1 NH_STOCK_STOCKSORT=1 NH_STOCK_NODARKFIX=1 NH_STOCK_NOTOPL=1 NH_STOCK_REALCLOCK=1 NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 NETHACKDIR=/workspace/nle-stock/build/nethackdir NLE_STOCK_LIB=/workspace/nle-stock/build/libnethack.so"
wait_final() { CK=$1; need=$2; lane=$3
  while true; do ck=$(ls $CK/ 2>/dev/null | grep -E '^[0-9]+\.bin$' | sort | tail -1); steps=$(echo "$ck" | sed 's/\.bin//; s/^0*//'); alive=$(ps -eo args | grep -c "[r]un_id=$lane\$"); [ -n "$steps" ] && [ "$steps" -ge $need ] && [ "$alive" = "0" ] && break; sleep 60; done; echo $ck; }
nomask_cert() { g=$1; lane=$2
  CK=/workspace/sweeps/nh/checkpoints/nethack/$lane; ck=$(wait_final $CK 3990000000 $lane); until gpu_idle $g; do sleep 30; done
  id=fork_${lane}_s7
  echo "$(date +%T) START $id = no-mask leaky 4B $lane ckpt $ck on its own engine (puffer $(md5sum $W/puffer | cut -c1-12) lib $(md5sum $W/vendor/fast-nle/build/libnethack.so | cut -c1-12)), NH_NO_CANT_HOLD=1 as trained, 14000 eps seed 7, gpu $g, nice 10 (A/B vs fork_nlestock4b_s60[1-4]_s7)" >> $L
  (cd $W && NH_NLE_OPTS=1 NH_NO_CANT_HOLD=1 NETHACKDIR=$W/vendor/fast-nle/build/dat NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$g nice -n 10 timeout 14400 ./puffer eval --headless --base.load_model_path=$CK/$ck --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=7 > $C/$id.out 2> $C/$id.err); rc=$?
  echo "$(date +%T) DONE $id rc=$rc eps=$(wc -l < $C/$id.ep) aborted=$(awk '$4>=1000{a++} END{print a+0}' $C/$id.ep) $(cd $W && python3 scripts/nle_stock/box/analyze.py $C/$id.ep | tail -1 | grep -oE 'burn-in.*')" >> $L; }
worker() { g=$1
  while true; do
    until gpu_idle $g; do sleep 30; done
    job=$(flock $Q.lock sh -c "head -1 $Q; sed -i 1d $Q"); [ -z "$job" ] && break
    set -- $job; kind=$1; lane=$2
    CK=/workspace/sweeps/nhfix/checkpoints/nethack/$lane; [ "$kind" = forkleaky ] && CK=/workspace/sweeps/nh/checkpoints/nethack/$lane
    case $lane in *1b_*) need=990000000;; *2b_*) need=1990000000;; *) need=3990000000;; esac
    ck=$(wait_final $CK $need $lane); WT=$CK/$ck
    if [ "$kind" = forkleaky ]; then id=fork_${lane}_s7
      echo "$(date +%T) START $id = leaky 4B $lane ckpt $ck on its own engine (puffer $(md5sum $W/puffer | cut -c1-12) lib $(md5sum $W/vendor/fast-nle/build/libnethack.so | cut -c1-12)), 14000 eps seed 7, gpu $g, nice 10" >> $L
      (cd $W && NH_NLE_OPTS=1 NETHACKDIR=$W/vendor/fast-nle/build/dat NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$g nice -n 10 timeout 14400 ./puffer eval --headless --base.load_model_path=$WT --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=7 > $C/$id.out 2> $C/$id.err); rc=$?
    elif [ "$kind" = fork ]; then id=fork_${lane}_s7
      echo "$(date +%T) START $id = leak-fixed $lane ckpt $ck, rung 1 on the fixed engine (puffer $(md5sum $F/puffer | cut -c1-12) lib $(md5sum $F/vendor/fast-nle/build/libnethack.so | cut -c1-12)), 14000 eps seed 7, gpu $g, nice 10" >> $L
      (cd $F && NH_NLE_OPTS=1 NETHACKDIR=$F/vendor/fast-nle/build/dat NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$g nice -n 10 timeout 14400 ./puffer eval --headless --base.load_model_path=$WT --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=7 > $C/$id.out 2> $C/$id.err); rc=$?
    else id=stock_${lane}_s21
      echo "$(date +%T) START $id = leak-fixed $lane ckpt $ck, stock strict seed 21 10000 default masks (stock $(md5sum $W/puffer_nethack_stock | cut -c1-12), tree $(git -C $W rev-parse --short HEAD)), gpu $g, nice 10" >> $L
      (cd $W && env $STOCKENV NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$g nice -n 10 timeout 21600 ./puffer_nethack_stock eval --headless --base.load_model_path=$WT --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 --base.eval_episodes=10000 --base.seed=21 > $C/$id.out 2> $C/$id.err); rc=$?
    fi
    echo "$(date +%T) DONE $id rc=$rc eps=$(wc -l < $C/$id.ep) aborted=$(awk '$4>=1000{a++} END{print a+0}' $C/$id.ep) $(cd $W && python3 scripts/nle_stock/box/analyze.py $C/$id.ep | tail -1 | grep -oE 'burn-in.*')" >> $L
  done; }
( nomask_cert 4 nlestock4b_nomask_s607; worker 4 ) &
( nomask_cert 6 nlestock4b_nomask_s608; worker 6 ) &
wait; echo "$(date +%T) CERTQ_EXTRA_DONE" >> $L
