#!/bin/bash
# The claim configuration, end to end: weights TRAINED on the conformant interface, scored on unmodified NetHack
# with NH_STOCK_STRICT=1 -- NLE's own default options, the challenge observation set, and the challenge step and
# no-progress limits. Nothing shifts between training and evaluation.
T=/workspace/PufferLib_pkg; L=/workspace/sweeps/nh/long.log; C=/workspace/sweeps/certq
cd $T; export NETHACKDIR=/workspace/nle-stock/build/nethackdir; ulimit -n 65536
cert() { gpu=$1; id=$2; w=$3; seed=$4
  echo "$(date +%T) gpu$gpu START $id STRICT (challenge interface)" >> $L; rm -f $C/$id.ep
  NH_STOCK_STRICT=1 NH_STOCK_CLEAREOS=1 NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_STALLCAP=1000000 \
    NLE_STOCK_LIB=/workspace/nle-stock/build/libnethack.so NH_EPLOG=$C/$id.ep CUDA_VISIBLE_DEVICES=$gpu \
    ./puffer_nethack_stock eval --headless --base.load_model_path=$w --policy.hidden_size=1024 --policy.num_layers=4 \
    --base.eval_agents=512 --base.eval_episodes=14000 --base.seed=$seed > $C/$id.out 2> $C/$id.err
  echo "$(date +%T) $id rc=$? strict_rc=$(grep -ac 'STRICT rc' $C/$id.err) aborts=$(grep -a '^CHALLENGE' $C/$id.err | grep -c 'aborted=1') $(python3 $C/analyze.py $C/$id.ep 2>&1 | tail -1 | cut -c1-140)" >> $L; }
A=/workspace/sweeps/nh/checkpoints/nethack/pkgnle_s406/0000000999817216.bin
B=/workspace/sweeps/nh/checkpoints/nethack/pkgnle_s407/0000000999817216.bin
cert 0 claim_406_s7  $A 7  & cert 1 claim_406_s11 $A 11 &
cert 2 claim_407_s7  $B 7  & cert 3 claim_407_s11 $B 11 &
wait; echo "$(date +%T) CLAIM_CERT_DONE" >> $L
