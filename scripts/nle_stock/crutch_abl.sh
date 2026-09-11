#!/bin/bash
# Price the two engine-memory crutches the gym binding cannot use, on the 532-game replay corpus.
S=/puffertank/pufferlib
cd /puffertank/pufferlib
W=resources/nethack/nethack_t1122_2B_weights.bin
A="eval --headless --base.load_model_path=$W --policy.hidden_size=1024 --policy.num_layers=4 --base.eval_agents=32 --base.eval_episodes=512"
export NETHACKDIR=/tmp/nle_stock_clang/build/nethackdir; export NLE_STOCK_LIB=/tmp/nle_stock_clang/build/libnethack.so
run() { # name, extra env
  local name=$1; shift
  echo "$(date +%T) start $name ($*)"
  env "$@" NH_HASH_FULL=1 NH_STOCK_STALLCAP=1000000 NH_KEYREPLAY=$S/keys_inv2 NH_STOCK_VERBOSE=1 \
    timeout 4000 ./puffer_nethack_stock $A > $S/crutch_${name}.out 2> $S/crutch_${name}.err
  echo "$(date +%T) $name rc=$? $(grep -a 'KEYREPLAY episodes' $S/crutch_${name}.err | tail -1)"
}
run ctl NH_STOCK_DUMMY=1
run nodark NH_STOCK_NODARKFIX=1
run notopl NH_STOCK_NOTOPL=1
run both NH_STOCK_NODARKFIX=1 NH_STOCK_NOTOPL=1
echo "$(date +%T) ALL DONE"
