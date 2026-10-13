#!/bin/bash
# After the main chain: sweep-mode smoke (forked trials), then long shipped-config runs (PR 300M, then base 300M) for crash/hang confidence.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad/pr693; R=$S/results.txt
while ! grep -q CHAIN_TESTS_DONE $R 2>/dev/null; do sleep 30; done
log(){ echo "[$(date -u +%T)] $*" | tee -a $R; }
export NETHACKDIR=/puffertank/pr693/vendor/fast-nle/build/dat
log "=== PR sweep smoke: 2 trials, 2-3M steps each (forked children)"
OUT=$S/sweep_pr; rm -rf $OUT; mkdir -p $OUT
( cd /puffertank/pr693 && timeout 900 ./puffer_nethack sweep --headless --sweep.max_runs=2 --sweep.train.total_timesteps.min=2000000 --sweep.train.total_timesteps.max=3000000 --base.eval_episodes=100 --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs > $OUT/run.log 2>&1; echo "SWEEP rc=$? trials_logged=$(ls $OUT/logs/nethack 2>/dev/null | wc -l) err_lines=$(grep -ciE 'assert|error|abort' $OUT/run.log)" | tee -a $R )
source_run(){ local T=$1 TAG=$2; shift 2; local OUT=$S/run_$TAG; rm -rf $OUT; mkdir -p $OUT; export NETHACKDIR=$T/vendor/fast-nle/build/dat
  ( cd $T && ./puffer_nethack train --headless --base.run_id=$TAG --base.checkpoint_dir=$OUT/ckpt --base.log_dir=$OUT/logs "$@" > $OUT/run.log 2>&1; echo $? > $OUT/rc )
  local sps=$(grep -oE 'SPS\s+[0-9.]+K' $OUT/run.log | awk '{print $2}' | tr -d K | awk 'NR>1{a[NR]=$1} END{n=asort(a); if(n==0){print "na"; exit} s=0;c=0; for(i=int(n/2)+1;i<=n;i++){s+=a[i];c++} printf "%.1fK", s/c}')
  log "LONG $TAG rc=$(cat $OUT/rc) sps_median_half=$sps final_score=$(grep -oE 'score[: ]+[0-9.]+' $OUT/run.log | tail -1 | awk '{print $NF}') err_lines=$(grep -ciE 'assert|error|segfault|abort' $OUT/run.log) uptime=$(grep -oE 'Uptime[^│]*' $OUT/run.log | tail -1 | tr -s ' ')"; }
log "=== long shipped-config runs: 300M steps, async=1, 4 buffers, full inline eval"
source_run /puffertank/pr693 pr_300m --train.total_timesteps=300000000
source_run /puffertank/pr693-base base_300m --train.total_timesteps=300000000
echo FOLLOWUP_DONE | tee -a $R
