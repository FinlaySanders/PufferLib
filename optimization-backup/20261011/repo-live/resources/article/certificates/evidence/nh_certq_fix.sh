#!/bin/bash
# ONE cert queue for the night (replaces nh_certq.sh + the first nh_certq_fix.sh): certs of the leak-fixed lanes as they land, and the own-engine fork certs of the four finished leaky 4B lanes: rung-1 fork cert on the FIXED engine (14000, seed 7) and stock strict rung 3 (10000, seed 21, default masks).
# Same idle-GPU rule as nh_certq.sh; a fork eval (7.5 GB) and a stock eval (12 GB) may share a card.
F=/workspace/pufferlib_fix; W=/workspace/pufferlib; C=/workspace/sweeps/certq/equiv; L=$C/equiv.log; Q=/workspace/sweeps/nhfix/certq_fix; ulimit -n 65536
printf "fork fixwt1b_s701\nstock fixwt1b_s701\nfork fixwt1b_s702\nstock fixwt1b_s702\nforkleaky nlestock4b_s602\nforkleaky nlestock4b_s601\nforkleaky nlestock4b_s603\nforkleaky nlestock4b_s604\nfork fixwt2b_s703\nstock fixwt2b_s703\nfork fixwt2b_s704\nstock fixwt2b_s704\nfork fixwt4b_s705\nstock fixwt4b_s705\nfork fixwt4b_s706\nstock fixwt4b_s706\n" > $Q
until [ ! -s /workspace/sweeps/nhfix/queue ]; do sleep 60; done; sleep 180
gpu_idle() { [ -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader --id=$1 2>/dev/null)" ]; }
STOCKENV="NH_STOCK_STRICT=1 NH_STOCK_LITERALOPTS= NH_STOCK_NOSDESC=1 NH_STOCK_NOREDRAW=1 NH_STOCK_STOCKSORT=1 NH_STOCK_NODARKFIX=1 NH_STOCK_NOTOPL=1 NH_STOCK_REALCLOCK=1 NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 NETHACKDIR=/workspace/nle-stock/build/nethackdir NLE_STOCK_LIB=/workspace/nle-stock/build/libnethack.so"
worker() { g=$1
  while true; do
    until gpu_idle $g; do sleep 30; done
    job=$(flock $Q.lock sh -c "head -1 $Q; sed -i 1d $Q"); [ -z "$job" ] && break
    set -- $job; kind=$1; lane=$2
    CK=/workspace/sweeps/nhfix/checkpoints/nethack/$lane; [ "$kind" = forkleaky ] && CK=/workspace/sweeps/nh/checkpoints/nethack/$lane
    case $lane in *1b_*) need=990000000;; *2b_*) need=1990000000;; *) need=3990000000;; esac
    # gate on the FINAL checkpoint and the trainer's exit -- never on a DONE log line (stale ones exist from the 17:33 false launch)
    while true; do ck=$(ls $CK/ 2>/dev/null | grep -E '^[0-9]+\.bin$' | sort | tail -1); steps=$(echo "$ck" | sed 's/\.bin//; s/^0*//'); alive=$(ps -eo args | grep -c "[r]un_id=$lane\$"); [ -n "$steps" ] && [ "$steps" -ge $need ] && [ "$alive" = "0" ] && break; sleep 60; done
    WT=$CK/$ck
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
for g in 0 1 2 3 5 7; do worker $g & sleep 2; done; wait; echo "$(date +%T) CERTQ_FIX_DONE" >> $L
