#!/bin/bash
# 32 MB workspace variant of the PR: build, then gate (2M) + h512 configs + breakout 300M; compare hashes with base/PR (4 MB). Then the 20M shipped-config SPS pair.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693; R=$S/ws32.txt; : > $R
while ! grep -q MATRIX3_DONE $S/matrix3.txt 2>/dev/null; do sleep 20; done
log(){ echo "$*" | tee -a $R; }
cd /puffertank/pr693-ws32 && ./build.sh nethack puffer_nethack > build_nethack.log 2>&1; log "ws32 build nethack rc=$?"; ./build.sh breakout puffer_breakout > build_breakout.log 2>&1; log "ws32 build breakout rc=$?"
one(){ local T=$1 B=$2 TAG=$3 N=$4; shift 4; local OUT=$S/w_$TAG; rm -rf $OUT; mkdir -p $OUT; export NETHACKDIR=$T/vendor/fast-nle/build/dat
  ( cd $T && timeout 1500 ./$B train --headless --base.seed=${SEED:-73} --base.run_id=$TAG --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs --train.total_timesteps=$N "$@" > $OUT/run.log 2>&1; echo $? > $OUT/rc )
  local ck=$(ls -t $OUT/ckpt/*/$TAG/*.bin 2>/dev/null | head -1); local sps=$(grep -oE 'SPS\s+[0-9.]+[KM]' $OUT/run.log | awk '{print $2}' | sed 's/K/e3/;s/M/e6/' | awk '{printf "%.0f\n",$1+0}' | sort -g | awk '{a[NR]=$1} END{if(NR==0){print "na";exit} s=0;c=0; for(i=int(NR/2)+1;i<=NR;i++){s+=a[i];c++} printf "%.0fK", s/c/1000}')
  echo "rc=$(cat $OUT/rc) sha=$(sha256sum "$ck" 2>/dev/null | cut -c1-16) sps=$sps score=$(grep -oE 'score\s+-?[0-9.]+' $OUT/run.log | tail -1 | awk '{print $NF}') err=$(grep -ciE 'assert|segfault|abort|nan' $OUT/run.log)"
}
W=/puffertank/pr693-ws32
log "gate_ws32 $(SEED=42 one $W puffer_nethack gate_ws32 2000000 --base.async=0 --vec.num_buffers=1 --base.eval_episodes=256)  [base/PR 4MB: b77d4f402f2a8ec6]"
log "h512_b1_ws32 $(one $W puffer_nethack h512b1_ws32 5000000 --vec.num_buffers=1 --base.eval_episodes=100)  [base/PR 4MB: 0c28ad9c32e7bf52]"
log "h128_b4_ws32 $(one $W puffer_nethack h128b4_ws32 5000000 --train.horizon=128 --base.eval_episodes=100)  [base/PR 4MB: c655deabe0ddc266]"
log "shipped_ws32_a $(one $W puffer_nethack ship_ws32_a 5000000 --base.eval_episodes=0)  [PR 4MB: d8b8187a790c67c8]"
log "shipped_ws32_b $(one $W puffer_nethack ship_ws32_b 5000000 --base.eval_episodes=0)"
log "breakout300m_ws32 $(one $W puffer_breakout bk_ws32 300000000 --base.eval_episodes=100)  [base/PR 4MB: 61da9aac0ce2d5b8]"
log "=== shipped-config SPS confirmation, 20M steps, eval skipped, idle GPU"
for T in base pr; do D=/puffertank/pr693; [ $T = base ] && D=/puffertank/pr693-base; log "ship20m_$T $(one $D puffer_nethack ship20m_$T 20000000 --base.eval_episodes=0)"; done
echo WS32_DONE | tee -a $R
