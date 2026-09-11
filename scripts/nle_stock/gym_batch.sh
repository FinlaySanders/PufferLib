#!/bin/bash
S=/puffertank/pufferlib
W=${W:-20}; EPS=${EPS:-30}; OUT=${OUT:-$S/cert/gym/run1}
mkdir -p $OUT; cd $S
for i in $(seq 1 $W); do
  setsid nohup python $S/scripts/nle_stock/nhc_agent.py --episodes $EPS --out $OUT/w$i.jsonl \
    > $OUT/w$i.log 2>&1 < /dev/null &
done
echo "launched $W workers x $EPS episodes -> $OUT"
