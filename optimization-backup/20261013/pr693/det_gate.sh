#!/bin/bash
# Determinism gate: 2M steps, seed 42, async=0, num_buffers=1, eval_episodes=256 → sha256 of the final checkpoint (first 16 hex).
# usage: det_gate.sh <tree> <tag>   (tree = /puffertank/pr693 or /puffertank/pr693-base)
T=$1; TAG=$2; OUT=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693/gate_$TAG; rm -rf $OUT; mkdir -p $OUT
export NETHACKDIR=$T/vendor/fast-nle/build/dat
cd $T && t0=$(date +%s); ./puffer_nethack train --headless --base.seed=42 --base.async=0 --vec.num_buffers=1 --base.eval_episodes=256 \
  --train.total_timesteps=2000000 --base.run_id=gate_$TAG --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs > $OUT/run.log 2>&1; rc=$?
ck=$(ls -t $OUT/ckpt/nethack/gate_$TAG/*.bin 2>/dev/null | head -1)
echo "GATE $TAG rc=$rc wall=$(( $(date +%s)-t0 ))s ckpt=$(basename "$ck" 2>/dev/null) sha=$(sha256sum "$ck" 2>/dev/null | cut -c1-16) score=$(grep -oE 'score[: ]+[0-9.]+' $OUT/run.log | tail -1)"
