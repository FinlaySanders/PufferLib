#!/bin/bash
# 1B retrain on the corrected public export (eager identity, canonical gems, engulf/engraving belief, pile_limit:0): 3 seeds, waits for the attribution arms
R=/workspace/sweeps/certq/results.log; while ! grep -q "ATTR2_DONE" $R; do sleep 30; done
L=/workspace/sweeps/nh/long.log; cd /workspace/sweeps/nh; export NETHACKDIR=/workspace/PufferLib/vendor/fast-nle/build/dat; ulimit -n 65536
f=$(ls trials/sweep_*_1122.ini | head -1); ARGS=$(python3 trial_args.py $f)
lane() { gpu=$1; seed=$2; id=rt_1B_1122new_s$seed; echo "$(date +%T) gpu$gpu START $id NEW-EXPORT 1B (lib $(md5sum /workspace/PufferLib/vendor/fast-nle/build/libnethack.so | cut -c1-12))" >> $L
  CUDA_VISIBLE_DEVICES=$gpu timeout 36000 /workspace/PufferLib/puffer train $ARGS --train.total_timesteps=1000000000 --base.seed=$seed --base.run_id=$id > panel_$id.out 2> panel_$id.err
  echo "$(date +%T) gpu$gpu $id rc=$? $(grep -a "env/score" /workspace/PufferLib/logs/nethack/$id.ini 2>/dev/null | awk -F"[ ,]" "{print \"score=\"\$NF}")" >> $L; }
lane 0 301 & lane 1 302 & lane 2 303 & wait; echo "$(date +%T) NEW_1B_DONE" >> $L
