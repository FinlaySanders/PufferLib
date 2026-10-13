#!/bin/bash
# NetHack determinism: shipped config (horizon 512, 4 buffers, async) x2 per tree; then 1 buffer h512; then 4 buffers h128. 20M steps each.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693; R=$S/nethack_det.txt; : > $R
log(){ echo "$*" | tee -a $R; }
one(){ local T=$1 TAG=$2; shift 2; local OUT=$S/nd_$TAG; rm -rf $OUT; mkdir -p $OUT; export NETHACKDIR=$T/vendor/fast-nle/build/dat
  ( cd $T && timeout 1500 ./puffer_nethack train --headless --base.seed=73 --base.run_id=$TAG --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs --train.total_timesteps=5000000 --base.eval_episodes=100 "$@" > $OUT/run.log 2>&1; echo $? > $OUT/rc )
  local ck=$(ls -t $OUT/ckpt/*/$TAG/*.bin 2>/dev/null | head -1)
  echo "rc=$(cat $OUT/rc) sha=$(sha256sum "$ck" 2>/dev/null | cut -c1-16) score_final=$(grep -oE 'score\s+-?[0-9.]+' $OUT/run.log | tail -1 | awk '{print $NF}') err=$(grep -ciE 'assert|segfault|abort|nan' $OUT/run.log) uptime=$(grep -oE 'Uptime\s+[0-9a-z ]+' $OUT/run.log | tail -1 | awk '{$1="";print}' | tr -s ' ')"
}
cfg(){ local NAME=$1; shift; for T in base pr; do D=/puffertank/pr693; [ $T = base ] && D=/puffertank/pr693-base; for rep in a b; do log "$NAME $T $rep $(one $D ${NAME}_${T}_$rep "$@")"; done; done
  sa=$(grep -E "^$NAME base a " $R | grep -oE 'sha=[0-9a-f]+'); sb=$(grep -E "^$NAME base b " $R | grep -oE 'sha=[0-9a-f]+'); pa=$(grep -E "^$NAME pr a " $R | grep -oE 'sha=[0-9a-f]+'); pb=$(grep -E "^$NAME pr b " $R | grep -oE 'sha=[0-9a-f]+')
  log "$NAME SUMMARY base_deterministic=$([ -n "$sa" ] && [ "$sa" = "$sb" ] && echo yes || echo NO) pr_deterministic=$([ -n "$pa" ] && [ "$pa" = "$pb" ] && echo yes || echo NO) pr_equals_base=$([ "$pa" = "$sa" ] && echo yes || echo no)"; }
cfg shipped_h512_b4
cfg h512_b1_async --vec.num_buffers=1
cfg h128_b4_async --train.horizon=128
cfg h512_b4_sync --base.async=0
echo NETHACK_DET_DONE | tee -a $R
