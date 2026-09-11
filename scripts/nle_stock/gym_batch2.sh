#!/bin/bash
S=/puffertank/pufferlib
W=${W:-12}; EPS=${EPS:-30}; OUT=$1; WEIGHTS=$2
mkdir -p $OUT; cd $S
for i in $(seq 1 $W); do
  setsid nohup python $S/scripts/nle_stock/nhc_agent.py --episodes $EPS --weights $WEIGHTS --out $OUT/w$i.jsonl \
    > $OUT/w$i.log 2>&1 < /dev/null &
done
echo "launched $W x $EPS on $(basename $WEIGHTS) -> $OUT"
