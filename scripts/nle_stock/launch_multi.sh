#!/bin/bash
# All-role paired arms: same weights, same seeds, fork engine vs stock C backend,
# NLE's option set. NH_MULTI=1 is what the challenge does (random role per reset).
S=/puffertank/pufferlib
N=$S/scripts/nle_stock
mkdir -p $S/cert/mfork $S/cert/mstock
cd $S
W=resources/nethack/nethack_t1122_2B_weights.bin
for i in $(seq 1 8); do
  NH_MULTI=1 NH_NLE_OPTS=1 NH_SEED=$((9000+i)) \
    setsid nohup $N/nh_cpu_fork $W 25 > $S/cert/mfork/w$i.out 2> $S/cert/mfork/w$i.err < /dev/null &
done
for i in $(seq 1 8); do
  NH_MULTI=1 NH_NLE_OPTS=1 NH_SEED=$((9000+i)) NH_STOCK_STALLCAP=1000000 \
  NH_STOCK_TERRAIN_PROBE=1 NH_STOCK_CLEAREOS=1 \
  NETHACKDIR=/puffertank/nle-stock/nle/nethackdir \
  NLE_STOCK_LIB=/puffertank/nle-stock/nle/libnethack.so \
    setsid nohup $N/nh_cpu_stock $W 25 > $S/cert/mstock/w$i.out 2> $S/cert/mstock/w$i.err < /dev/null &
done
sleep 2
echo "launched 8 fork + 8 stock, all roles, NLE options"
