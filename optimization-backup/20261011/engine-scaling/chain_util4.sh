#!/bin/bash
# per-thread utilisation inside 44-epoch runs: control (47 s) window 20-42 s, cohort (~40 s) window 18-36 s
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; H=/puffertank/experiments/nethack-24h-20261009; cd $H
while ! grep -q "CHAIN_VALIDATE3_DONE" $S/chain_validate3.log; do sleep 5; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 campaign_ablate.py ablate_util4.json &
for L in util4_ctrl:20:42 util4_env:18:36; do IFS=: read NAME T1 T2 <<<"$L"
  while ! PID=$(pgrep -f "^/puffertank/experiments/nethack-24h-20261009/binaries/cohort_ini .*" | head -1) || [ -z "$PID" ] || ! grep -q "$NAME" /proc/$PID/cmdline 2>/dev/null; do sleep 1; done
  echo "ATTACH $NAME pid=$PID $(date -u +%T)"
  ./thread_util.sh $PID $T1 $T2 | sed "s/^/$NAME: /"
  while [ -d /proc/$PID ]; do sleep 1; done
done
wait; echo CHAIN_UTIL4_DONE
