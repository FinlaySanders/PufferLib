#!/bin/bash
# burn-in standalone evals: 4000 warm-up games, then 10K counted games, 512 agents, verb_eps 0
cd /workspace/sweeps/nh; export NETHACKDIR=/workspace/PufferLib/vendor/fast-nle/build/dat; ulimit -n 65536; L=eval_burnin.log; : > $L
freegpu() { for g in 0 1 2 3 4 5 6 7; do busy=$(nvidia-smi --query-compute-apps=gpu_bus_id --format=csv,noheader 2>/dev/null | grep -c "$(nvidia-smi --query-gpu=gpu_bus_id --format=csv,noheader -i $g)"); [ "$busy" = "0" ] && { echo $g; return; }; done; echo ""; }
for pair in "0899 rt_1B_0899_s201" "0781 rt_1B_0781_s201" "0742 rt_1B_0742_s201" "0865 rt_1B_0865_s201" "0973 rt_2B_0973_s201" "0973 rt_1B_0973_s201"; do set -- $pair; trial=$1; id=$2
  ck=$(ls checkpoints/nethack/$id/*.bin | sort | tail -1); ARGS=$(python3 trial_args.py $(ls trials/sweep_*_$trial.ini | head -1))
  while true; do g=$(freegpu); [ -n "$g" ] && break; sleep 60; done
  echo "$(date +%T) gpu$g EVAL $id ckpt $(basename $ck)" >> $L
  CUDA_VISIBLE_DEVICES=$g timeout 7200 ./puffer_burnin eval $ck --headless $ARGS --base.burnin_games=4000 --base.eval_agents=512 --base.eval_episodes=10000 > evalb_$id.log 2>&1
  echo "$(date +%T) $id rc=$? $(grep -a "CUDA_EVAL" evalb_$id.log | tail -1 | grep -o "score=[0-9.]*\|games=[0-9]*" | tr "\n" " ") | $(grep -a "burn-in done" evalb_$id.log | tail -1)" >> $L
done; echo "$(date +%T) EVAL_BURNIN_DONE" >> $L
