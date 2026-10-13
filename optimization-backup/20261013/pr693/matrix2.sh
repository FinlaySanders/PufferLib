#!/bin/bash
# Pass 2: longer budgets so learning is visible (30-90 s per run); one run per tree per env (pass 1 established within-tree determinism),
# plus nethack shipped config x2 per tree (known pipeline race, expected nondeterministic on both) and nethack async=0 (deterministic).
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693; R=$S/matrix2.txt
while ! grep -q NETHACK_DET_DONE $S/nethack_det.txt 2>/dev/null; do sleep 15; done
log(){ echo "$*" | tee -a $R; }
one(){ local T=$1 E=$2 B=$3 TAG=$4 N=$5; shift 5; local OUT=$S/m2_$TAG; rm -rf $OUT; mkdir -p $OUT; export NETHACKDIR=$T/vendor/fast-nle/build/dat
  ( cd $T && timeout 1200 ./$B train --headless --base.seed=73 --base.run_id=$TAG --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs --train.total_timesteps=$N --base.eval_episodes=100 "$@" > $OUT/run.log 2>&1; echo $? > $OUT/rc )
  local ck=$(ls -t $OUT/ckpt/*/$TAG/*.bin 2>/dev/null | head -1); local sha=$(sha256sum "$ck" 2>/dev/null | cut -c1-16)
  local sps=$(grep -oE 'SPS\s+[0-9.]+[KM]' $OUT/run.log | awk '{print $2}' | sed 's/K/e3/;s/M/e6/' | awk '{printf "%.0f\n",$1+0}' | sort -g | awk '{a[NR]=$1} END{if(NR==0){print "na";exit} s=0;c=0; for(i=int(NR/2)+1;i<=NR;i++){s+=a[i];c++} printf "%.0fK", s/c/1000}')
  local scores=$(grep -oE 'score\s+-?[0-9.]+' $OUT/run.log | awk '{print $NF}' | tr '\n' ' '); local n=$(echo $scores | wc -w); local mid=$(echo $scores | awk '{print $(int(NF/2)+1)}'); local last=$(echo $scores | awk '{print $NF}')
  echo "rc=$(cat $OUT/rc) sha=${sha:-none} score_mid=$mid score_final=$last sps=$sps err=$(grep -ciE 'assert|segfault|abort|nan' $OUT/run.log) uptime=$(grep -oE 'Uptime\s+[0-9a-z ]+' $OUT/run.log | tail -1 | awk '{$1="";print}' | tr -s ' ')"
}
declare -A STEPS=( [breakout]=300000000 [breakout_cu]=300000000 [pong]=50000000 [snake]=150000000 [squared]=100000000 [tetris]=150000000 [connect4]=50000000 [drone]=150000000 [cartpole]=50000000 [asteroids]=150000000 )
for E in snake squared tetris connect4 drone cartpole asteroids; do
  for T in base pr; do D=/puffertank/pr693; [ $T = base ] && D=/puffertank/pr693-base; log "$E $T $(one $D $E puffer_$E ${E}_${T} ${STEPS[$E]})"; done
  sb=$(grep -E "^$E base " $R | grep -oE 'sha=[0-9a-f]+'); sp=$(grep -E "^$E pr " $R | grep -oE 'sha=[0-9a-f]+'); log "$E SUMMARY pr_equals_base=$([ -n "$sb" ] && [ "$sb" = "$sp" ] && echo yes || echo NO)"
done
echo MATRIX2_DONE | tee -a $R
