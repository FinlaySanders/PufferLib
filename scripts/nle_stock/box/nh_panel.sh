#!/bin/bash
# NetHack seed panel: replay top sweep trials with fresh seeds, 6 GPU workers (GPUs 2,3 belong to the drone free sweep)
cd /workspace/sweeps/nh; export NETHACKDIR=/workspace/PufferLib/vendor/fast-nle/build/dat; ulimit -n 65536
Q=/workspace/sweeps/nh/panel_jobs.txt; L=/workspace/sweeps/nh/panel.log; : > $L; : > $Q
for trial in 0742 0865 0899 0781 0916 0894; do for seed in 101 102 103; do echo "$trial $seed" >> $Q; done; done
echo "$(date +%T) queued $(wc -l < $Q) runs" >> $L
worker() { gpu=$1; while true; do
  job=$(flock $Q.lock sh -c "head -1 $Q; sed -i 1d $Q"); [ -z "$job" ] && break
  set -- $job; trial=$1; seed=$2; id=rt_nh${trial}_s$seed
  f=$(ls trials/sweep_*_$trial.ini | head -1); ARGS=$(python3 trial_args.py $f)
  CUDA_VISIBLE_DEVICES=$gpu timeout 7200 ./puffer_nethack train $ARGS --base.seed=$seed --base.run_id=$id > panel_runs_$id.log 2>&1
  echo "$(date +%T) gpu$gpu $id rc=$? $(grep -a "env/score" logs/nethack/$id.ini 2>/dev/null | awk -F"[ ,]" "{print \"score=\"\$NF}")" >> $L
done; }
for g in 0 1 4 5 6 7; do worker $g & done; wait
echo "$(date +%T) NH_PANEL_DONE" >> $L
