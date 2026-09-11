#!/bin/bash
# overnight long-run lanes. usage: nh_long.sh <own_queue> <fallback_queue> <gpus...>
# job line: trial seed steps [extra train args]; id rt_<steps>_<trial>_s<seed>
cd /workspace/sweeps/nh; export NETHACKDIR=/workspace/PufferLib/vendor/fast-nle/build/dat; ulimit -n 65536
OWN=$1; FB=$2; shift 2; L=/workspace/sweeps/nh/long.log
take() { for Q in $OWN $FB; do j=$(flock $Q.lock sh -c "head -1 $Q; sed -i 1d $Q"); [ -n "$j" ] && { echo "$j"; return; }; done; }
worker() { gpu=$1; while true; do
  job=$(take); [ -z "$job" ] && break
  set -- $job; trial=$1; seed=$2; steps=$3; shift 3; extra="$*"; tag=$(( steps / 1000000000 ))B; id=rt_${tag}_${trial}_s$seed
  f=$(ls trials/sweep_*_$trial.ini | head -1); ARGS=$(python3 trial_args.py $f)
  echo "$(date +%T) gpu$gpu START $id $extra" >> $L
  CUDA_VISIBLE_DEVICES=$gpu timeout 36000 ./puffer_nethack train $ARGS --train.total_timesteps=$steps $extra --base.seed=$seed --base.run_id=$id > panel_runs_$id.log 2>&1
  echo "$(date +%T) gpu$gpu $id rc=$? $(grep -a "env/score" logs/nethack/$id.ini 2>/dev/null | awk -F"[ ,]" "{print \"score=\"\$NF}")" >> $L
done; }
for g in "$@"; do worker $g & done; wait
echo "$(date +%T) LANE_DONE $OWN" >> $L
