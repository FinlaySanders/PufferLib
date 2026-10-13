#!/bin/bash
# Determinism + no-breakage matrix: each env trained twice per tree (same seed, default ini, async as shipped) → final-checkpoint sha256, score, SPS.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693; R=$S/matrix.txt; : > $R
while ! grep -q BUILD_ENVS_DONE $S/build_envs.log 2>/dev/null; do sleep 10; done
for T in /puffertank/pr693 /puffertank/pr693-base; do (cd $T && [ -x puffer_breakout_cu ] || ./build.sh breakout puffer_breakout_cu --cu > build_breakout_cu.log 2>&1; echo "$(basename $T) breakout_cu rc=$?" >> $S/build_envs.log); done
log(){ echo "$*" | tee -a $R; }
one(){ # one <tree> <env> <bin> <tag> <steps>
  local T=$1 E=$2 B=$3 TAG=$4 N=$5; local OUT=$S/m_$TAG; rm -rf $OUT; mkdir -p $OUT; export NETHACKDIR=$T/vendor/fast-nle/build/dat
  ( cd $T && timeout 600 ./$B train --headless --base.seed=73 --base.run_id=$TAG --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs --train.total_timesteps=$N --base.eval_episodes=50 > $OUT/run.log 2>&1; echo $? > $OUT/rc )
  local ck=$(ls -t $OUT/ckpt/*/$TAG/*.bin 2>/dev/null | head -1); local sha=$(sha256sum "$ck" 2>/dev/null | cut -c1-16)
  local sps=$(grep -oE 'SPS\s+[0-9.]+[KM]' $OUT/run.log | awk '{print $2}' | sed 's/K/e3/;s/M/e6/' | awk '{a[NR]=$1+0} END{n=asort(a); if(n==0){print "na";exit} s=0;c=0; for(i=int(n/2)+1;i<=n;i++){s+=a[i];c++} printf "%.0fK", s/c/1000}')
  local score=$(grep -oE 'score[: ]+-?[0-9.]+' $OUT/run.log | tail -1 | awk '{print $NF}'); local err=$(grep -ciE 'assert|error|segfault|abort|nan' $OUT/run.log)
  echo "rc=$(cat $OUT/rc) sha=${sha:-none} score=${score:-na} sps=$sps err=$err"
}
ENVS="breakout breakout_cu pong snake squared tetris connect4 drone cartpole asteroids"
for E in $ENVS; do
  N=10000000; case $E in snake|drone) N=20000000;; esac
  for T in base pr; do D=/puffertank/pr693; [ $T = base ] && D=/puffertank/pr693-base; [ -x $D/puffer_$E ] || { log "$E $T: NO BINARY"; continue; }
    for rep in a b; do r=$(one $D $E puffer_$E ${E}_${T}_$rep $N); log "$E $T $rep $r"; done
  done
  sa=$(grep -E "^$E base a " $R | grep -oE 'sha=[0-9a-f]+' | cut -d= -f2); sb=$(grep -E "^$E base b " $R | grep -oE 'sha=[0-9a-f]+' | cut -d= -f2)
  pa=$(grep -E "^$E pr a " $R | grep -oE 'sha=[0-9a-f]+' | cut -d= -f2); pb=$(grep -E "^$E pr b " $R | grep -oE 'sha=[0-9a-f]+' | cut -d= -f2)
  log "$E SUMMARY base_deterministic=$([ -n "$sa" ] && [ "$sa" = "$sb" ] && echo yes || echo NO) pr_deterministic=$([ -n "$pa" ] && [ "$pa" = "$pb" ] && echo yes || echo NO) pr_equals_base=$([ -n "$pa" ] && [ "$pa" = "$sa" ] && echo yes || echo no)"
done
echo MATRIX_DONE | tee -a $R
