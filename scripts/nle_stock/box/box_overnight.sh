#!/bin/bash
# ~12h queue. Round 1 on the six idle GPUs; round 2 as each round-1 job exits.
# Every arm runs on the SAME package build, differing only by env var, so the comparisons are clean.
T=/workspace/PufferLib_pkg; L=/workspace/sweeps/nh/long.log; C=/workspace/sweeps/certq
cd /workspace/sweeps/nh; export NETHACKDIR=$T/vendor/fast-nle/build/dat; ulimit -n 65536
while ! grep -q PKG_BUILD_OK $L; do sleep 30; done
f=$(ls trials/sweep_*_1122.ini | head -1); ARGS=$(python3 trial_args.py $f)

lane() { # gpu seed id extra_env
  gpu=$1; seed=$2; id=$3; shift 3
  echo "$(date +%T) gpu$gpu START $id [$*] lib $(md5sum $T/vendor/fast-nle/build/libnethack.so | cut -c1-12)" >> $L
  env "$@" CUDA_VISIBLE_DEVICES=$gpu timeout 39600 $T/puffer train $ARGS --train.total_timesteps=1000000000 \
      --base.seed=$seed --base.run_id=$id > panel_$id.out 2> panel_$id.err
  echo "$(date +%T) gpu$gpu $id rc=$? score=$(tr '\r' '\n' < panel_$id.out | grep -a -oE 'score +[0-9]+\.[0-9]+' | tail -1 | tr -s ' ')" >> $L
}
cert() { # gpu id weights seed
  gpu=$1; id=$2; w=$3; seed=$4
  echo "$(date +%T) gpu$gpu START cert $id (current derive)" >> $L
  rm -f $C/$id.ep
  cd $T
  NH_STOCK_CLEAREOS=1 NETHACKDIR=/workspace/nle-stock/build/nethackdir NLE_STOCK_LIB=/workspace/nle-stock/build/libnethack.so \
    NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    ./puffer_nethack_stock eval --headless --base.load_model_path=$w --policy.hidden_size=1024 --policy.num_layers=4 \
    --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=$seed > $C/$id.out 2> $C/$id.err
  echo "$(date +%T) cert $id rc=$? $(python3 $C/analyze.py $C/$id.ep 2>&1 | tail -1 | cut -c1-150)" >> $L
  cd /workspace/sweeps/nh
}
CH=$T/resources/nethack/nethack_t1122_2B_weights.bin
B4=$(ls /workspace/sweeps/nh/checkpoints/nethack/rt_4B_1122_s204/*.bin 2>/dev/null | sort | tail -1)

# ---- round 1 : package x3, autopickup-isolation x1, cert x2
( lane 1 401 pkg_s401 NH_DUMMY=0;                 lane 1 404 iso_s404 NH_NLE_OPTS=1 NH_KEEP_PILELIMIT=1 ) &
( lane 2 402 pkg_s402 NH_DUMMY=0;                 lane 2 405 iso_s405 NH_NLE_OPTS=1 NH_KEEP_PILELIMIT=1 ) &
( lane 3 403 pkg_s403 NH_DUMMY=0;                 lane 3 406 pkgnle_s406 NH_NLE_OPTS=1 ) &
( lane 5 411 iso_s411 NH_NLE_OPTS=1 NH_KEEP_PILELIMIT=1; lane 5 407 pkgnle_s407 NH_NLE_OPTS=1 ) &
( cert 6 cert_2b_s7  $CH 7;                       [ -n "$B4" ] && cert 6 cert_4b_s7 $B4 7 ) &
( cert 7 cert_2b_s11 $CH 11;                      cert 7 cert_2b_s13 $CH 13 ) &
wait
echo "$(date +%T) OVERNIGHT_QUEUE_DONE" >> $L
