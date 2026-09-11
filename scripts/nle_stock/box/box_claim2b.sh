#!/bin/bash
# Scale-up on the CLAIM CONFIGURATION: package export + full NLE default options, 2B steps.
# Every 1B result says conformance is free, so this is the run whose weights we would actually claim with.
T=/workspace/PufferLib_pkg; L=/workspace/sweeps/nh/long.log
cd /workspace/sweeps/nh; export NETHACKDIR=$T/vendor/fast-nle/build/dat; ulimit -n 65536
f=$(ls trials/sweep_*_1122.ini | head -1); ARGS=$(python3 trial_args.py $f)
lane() { gpu=$1; seed=$2; id=claim2b_s$seed
  echo "$(date +%T) gpu$gpu START $id 2B CLAIM-CONFIG (NLE opts, package lib $(md5sum $T/vendor/fast-nle/build/libnethack.so | cut -c1-12))" >> $L
  NH_NLE_OPTS=1 CUDA_VISIBLE_DEVICES=$gpu timeout 172800 $T/puffer train $ARGS \
    --train.total_timesteps=2000000000 --base.seed=$seed --base.run_id=$id > panel_$id.out 2> panel_$id.err
  echo "$(date +%T) gpu$gpu $id rc=$? marker=$(grep -ac 'NH_NLE_OPTS active' panel_$id.err) score=$(tr '\r' '\n' < panel_$id.out | grep -a -oE 'score +[0-9]+\.[0-9]+' | tail -1 | tr -s ' ')" >> $L; }
lane 1 501 & lane 2 502 & lane 3 503 & lane 5 504 &
wait; echo "$(date +%T) CLAIM_2B_DONE" >> $L
