#!/bin/bash
# PR 693 stability chain: profile-target classification, determinism gates, shipped-config stability (base vs PR), GPU env, eval, many-buffer config.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693; R=$S/results.txt; : > $R
log(){ echo "[$(date -u +%T)] $*" | tee -a $R; }
memmax(){ # background sampler of GPU memory while a pid runs
  local pid=$1 out=$2; local m=0; while kill -0 $pid 2>/dev/null; do v=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1); [ "$v" -gt "$m" ] 2>/dev/null && m=$v; sleep 2; done; echo $m > $out; }
run_train(){ # run_train <tree> <bin> <tag> <args...>  → logs under $S/run_<tag>; prints SPS stats, rc, max GPU mem, final score
  local T=$1 B=$2 TAG=$3; shift 3; local OUT=$S/run_$TAG; rm -rf $OUT; mkdir -p $OUT
  export NETHACKDIR=$T/vendor/fast-nle/build/dat
  ( cd $T && ./$B train --headless --base.run_id=$TAG --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs "$@" > $OUT/run.log 2>&1; echo $? > $OUT/rc ) &
  local pid=$!; sleep 3; local tp=$(pgrep -f "run_id=$TAG" | head -1); memmax ${tp:-$pid} $OUT/memmax & local mp=$!; wait $pid; wait $mp
  local rc=$(cat $OUT/rc); local sps=$(grep -oE 'SPS\s+[0-9.]+K' $OUT/run.log | awk '{print $2}' | tr -d K | awk 'NR>1{a[NR]=$1} END{n=asort(a); if(n==0){print "na"; exit} s=0;c=0; for(i=int(n/2)+1;i<=n;i++){s+=a[i];c++} printf "%.1fK(median-half mean) max=%.1fK", s/c, a[n]}')
  local score=$(grep -oE 'score[: ]+[0-9.]+' $OUT/run.log | tail -1 | awk '{print $NF}'); local err=$(grep -ciE 'assert|error|segfault|abort' $OUT/run.log)
  log "RUN $TAG rc=$rc sps=$sps final_score=$score gpu_mem_max=$(cat $OUT/memmax)MiB err_lines=$err wall=$(grep -oE 'Uptime[^│]*' $OUT/run.log | tail -1 | tr -s ' ')"
}
cd /puffertank/pr693-base && ./build.sh nethack --profile > build_profile.log 2>&1; log "BASE profile-target build rc=$? (PR: rc=255, 100 errors in tests/profile_kernels.cu)"; grep -cE 'error' build_profile.log | xargs -I{} log "BASE profile errors={}"
log "=== determinism gates (2M steps, seed 42, async=0, 1 buffer)"
$S/det_gate.sh /puffertank/pr693-base base | tee -a $R; $S/det_gate.sh /puffertank/pr693 pr | tee -a $R
$S/det_gate.sh /puffertank/pr693 pr_rep | tee -a $R
log "=== shipped config stability: nethack 50M steps, async=1, 4 buffers, 512 agents, inline eval 1000 episodes"
run_train /puffertank/pr693-base puffer_nethack base_50m --train.total_timesteps=50000000 --base.eval_episodes=1000
run_train /puffertank/pr693 puffer_nethack pr_50m --train.total_timesteps=50000000 --base.eval_episodes=1000
log "=== GPU env: breakout default config 20M steps"
run_train /puffertank/pr693-base puffer_breakout base_breakout --train.total_timesteps=20000000 --base.eval_episodes=100
run_train /puffertank/pr693 puffer_breakout pr_breakout --train.total_timesteps=20000000 --base.eval_episodes=100
log "=== PR extra configs"
run_train /puffertank/pr693 puffer_nethack pr_buf16 --train.total_timesteps=10000000 --vec.num_buffers=16 --base.eval_episodes=200
run_train /puffertank/pr693 puffer_nethack pr_async0 --train.total_timesteps=10000000 --base.async=0 --base.eval_episodes=200
run_train /puffertank/pr693 puffer_nethack pr_buf1 --train.total_timesteps=10000000 --vec.num_buffers=1 --base.eval_episodes=200
log "=== PR standalone eval on the 50M checkpoint"
CK=$(ls -t $S/run_pr_50m/ckpt/nethack/pr_50m/*.bin 2>/dev/null | head -1); export NETHACKDIR=/puffertank/pr693/vendor/fast-nle/build/dat
( cd /puffertank/pr693 && ./puffer_nethack eval --headless --base.load_model_path=$CK --base.eval_episodes=500 --base.eval_agents=512 > $S/eval_pr.log 2>&1; echo "EVAL rc=$? $(grep -oE 'score[: ]+[0-9.]+' $S/eval_pr.log | tail -1) err_lines=$(grep -ciE 'assert|error|abort' $S/eval_pr.log)" | tee -a $R )
echo CHAIN_TESTS_DONE | tee -a $R
