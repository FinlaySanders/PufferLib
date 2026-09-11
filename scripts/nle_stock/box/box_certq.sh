#!/bin/bash
# cert queue on the drone box: 512 agents x 14000 episodes, seed given, per-episode log for burn-in; one job per GPU
cd /workspace/PufferLib; Q=/workspace/sweeps/certq/jobs.txt; R=/workspace/sweeps/certq/results.log; mkdir -p /workspace/sweeps/certq; : > $Q
CH=/workspace/PufferLib/resources/nethack/nethack_t1122_2B_weights.bin
B4=$(ls /workspace/sweeps/nh/checkpoints/nethack/rt_4B_1122_s204/*.bin 2>/dev/null | sort | tail -1)
P1=$(ls /workspace/sweeps/nh/checkpoints/nethack/rt_1B_1122pub_s301/*.bin 2>/dev/null | sort | tail -1)
echo "fork new2b_s7 $CH 7 15" >> $Q; echo "fork new2b_s11 $CH 11 15" >> $Q; echo "fork lazy2b_s7 $CH 7 7" >> $Q
echo "stock stock2b_s11 $CH 11 0" >> $Q; echo "stock stock2b_s7 $CH 7 0" >> $Q
[ -n "$B4" ] && { echo "fork new4b_s7 $B4 7 15" >> $Q; echo "stock stock4b_s7 $B4 7 0" >> $Q; }
[ -n "$P1" ] && { echo "stock stockpub301_s7 $P1 7 0" >> $Q; echo "fork forkpub301_s7 $P1 7 15" >> $Q; }
echo "$(date +%T) queued $(wc -l < $Q) runs; 4B=$B4 pub=$P1" >> $R
worker() { gpu=$1; while true; do
  job=$(flock $Q.lock sh -c "head -1 $Q; sed -i 1d $Q"); [ -z "$job" ] && break
  set -- $job; eng=$1; id=$2; f=$3; seed=$4; abl=$5
  A="eval --headless --base.load_model_path=$f --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=$seed"
  rm -f /workspace/sweeps/certq/$id.ep; echo "$(date +%T) START $id gpu$gpu" >> $R
  if [ $eng = stock ]; then NETHACKDIR=/workspace/nle-stock/build/nethackdir NLE_STOCK_LIB=/workspace/nle-stock/build/libnethack.so NH_STOCK_LAZYMAP= NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 NH_EPLOG=/workspace/sweeps/certq/$id.ep CUDA_VISIBLE_DEVICES=$gpu timeout 28800 ./puffer_nethack_stock $A > /workspace/sweeps/certq/$id.out 2> /workspace/sweeps/certq/$id.err; rc=$?
  else NLE_ABL=$abl NETHACKDIR=/workspace/PufferLib/vendor/fast-nle/build/dat NH_EPLOG=/workspace/sweeps/certq/$id.ep CUDA_VISIBLE_DEVICES=$gpu timeout 14400 ./puffer $A > /workspace/sweeps/certq/$id.out 2> /workspace/sweeps/certq/$id.err; rc=$?; fi
  echo "$(date +%T) DONE $id rc=$rc $(python3 /workspace/sweeps/certq/analyze.py /workspace/sweeps/certq/$id.ep 2>&1 | cut -c1-160)" >> $R
done; }
for g in 0 1 2 3 4 5 6 7; do worker $g & done; wait
echo "$(date +%T) CERTQ_DONE" >> $R
