#!/bin/bash
# Pool-worker utilisation: per-thread CPU time over the measured window, cohort config then control. Runs after the pool-timing chain.
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
while ! grep -q "CHAIN_POOLTIMING_DONE" $S/chain_pooltiming.log; do sleep 15; done; echo "WAIT_POOLTIMING_DONE $(date -u +%T)"
cd /puffertank/experiments/nethack-24h-20261009
python3 campaign_ablate.py ablate_util.json &
for L in util5_b16c4s64 util5_ctrl; do
  while ! pgrep -f "incpack_v39.*$L" >/dev/null && ! [ -d runs/$L ]; do sleep 1; done
  sleep 2; PID=$(pgrep -f "binaries/incpack_v39" | head -1); echo "ATTACH $L pid=$PID $(date -u +%T)"
  [ -n "$PID" ] && ./thread_util.sh $PID 25 25 | sed "s/^/$L: /"
  while pgrep -f "binaries/incpack_v39" >/dev/null; do sleep 2; done
done
wait; echo CHAIN_UTIL_DONE
