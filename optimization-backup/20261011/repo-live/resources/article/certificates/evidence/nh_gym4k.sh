#!/bin/bash
# 4,032-game python NetHackChallenge-v0 runs (144 workers x 28 games, equal-k) of each leak-fixed 4B as it lands (gate: final ckpt >= 3.99B + trainer exit), sequential.
W=/workspace/pufferlib; C=/workspace/sweeps/certq/equiv; L=$C/equiv.log; PY=/workspace/nle-venv/bin/python; ulimit -n 65536; cd $W
for lane in fixwt4b_s705 fixwt4b_s706; do CK=/workspace/sweeps/nhfix/checkpoints/nethack/$lane
  while true; do ck=$(ls $CK/ 2>/dev/null | grep -E '^[0-9]+\.bin$' | sort | tail -1); steps=$(echo "$ck" | sed 's/\.bin//; s/^0*//'); alive=$(ps -eo args | grep -c "[r]un_id=$lane\$"); [ -n "$steps" ] && [ "$steps" -ge 3990000000 ] && [ "$alive" = "0" ] && break; sleep 60; done
  d=$C/r4_${lane}_4k; mkdir -p $d; rm -f $d/*.jsonl $d/*.log
  echo "$(date +%T) START r4_${lane}_4k = python NetHackChallenge-v0, 144x28 = 4,032 games, leak-fixed 4B $lane ckpt $ck, libnhagent $(md5sum scripts/nle_stock/libnhagent.so | cut -c1-12), tree $(git rev-parse --short HEAD), nice 5" >> $L
  for i in $(seq 1 144); do nice -n 5 $PY scripts/nle_stock/nhc_agent.py --episodes 28 --weights $CK/$ck --out $d/w$i.jsonl > $d/w$i.log 2>&1 & done; wait
  echo "$(date +%T) DONE r4_${lane}_4k 144x28 $($PY scripts/nle_stock/gym_analyze.py $d 2>&1 | grep -E 'EQUAL-K|episode 1 median|end status' | tr '\n' ' ' | cut -c1-260)" >> $L
done
echo "$(date +%T) GYM4K_DONE" >> $L
