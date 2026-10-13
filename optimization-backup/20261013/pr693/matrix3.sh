#!/bin/bash
# Pass 3: GPU co-tenancy stress. The original symptom (cudaGraphLaunch assertion in a multi-buffer nethack run) appeared while another process
# shared the GPU. Run nethack shipped config (20M) with a concurrent breakout_cu trainer on the same GPU, 3 trials per tree; count asserts/crashes.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693; R=$S/matrix3.txt; : > $R
while ! grep -q MATRIX2_DONE $S/matrix2.txt 2>/dev/null; do sleep 15; done
log(){ echo "$*" | tee -a $R; }
for T in base pr; do D=/puffertank/pr693; [ $T = base ] && D=/puffertank/pr693-base; export NETHACKDIR=$D/vendor/fast-nle/build/dat
  for trial in 1 2 3; do OUT=$S/m3_${T}_$trial; rm -rf $OUT; mkdir -p $OUT
    ( cd $D && timeout 900 ./puffer_breakout_cu train --headless --base.seed=7 --base.run_id=cot_${T}_$trial --base.checkpoint_dir=$OUT/ckpt_b --base.log_dir=$OUT/logs_b --train.total_timesteps=400000000 --base.eval_episodes=10 > $OUT/breakout.log 2>&1; echo $? > $OUT/rc_b ) &
    sleep 4
    ( cd $D && timeout 900 ./puffer_nethack train --headless --base.seed=73 --base.run_id=cotnh_${T}_$trial --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs --train.total_timesteps=20000000 --base.eval_episodes=100 > $OUT/nethack.log 2>&1; echo $? > $OUT/rc )
    pkill -f "run_id=cot_${T}_$trial" || true; wait
    log "cotenancy $T $trial nethack_rc=$(cat $OUT/rc) nethack_asserts=$(grep -ciE 'assert|abort|segfault|cudaGraphLaunch' $OUT/nethack.log) breakout_rc=$(cat $OUT/rc_b 2>/dev/null) breakout_asserts=$(grep -ciE 'assert|abort|segfault|cudaGraphLaunch' $OUT/breakout.log) nethack_score=$(grep -oE 'score\s+-?[0-9.]+' $OUT/nethack.log | tail -1 | awk '{print $NF}')"
  done
done
echo MATRIX3_DONE | tee -a $R
