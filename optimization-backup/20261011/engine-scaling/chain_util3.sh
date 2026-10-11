#!/bin/bash
# Pool-worker utilisation, sampled inside the measured window (cohort 30-55 s, control 36-66 s of the run).
cd /puffertank/experiments/nethack-24h-20261009
python3 campaign_ablate.py ablate_util3.json &
for L in util3_b16c4s64:30:55 util3_ctrl:36:66; do IFS=: read NAME T1 T2 <<<"$L"
  while ! PID=$(pgrep -f "^/puffertank/experiments/nethack-24h-20261009/binaries/incpack_v39 .*" | head -1) || [ -z "$PID" ] || ! grep -q "$NAME" /proc/$PID/cmdline 2>/dev/null; do sleep 1; done
  echo "ATTACH $NAME pid=$PID $(date -u +%T) threads=$(ls /proc/$PID/task | wc -l)"
  ./thread_util.sh $PID $T1 $((T2)) | sed "s/^/$NAME: /"
  while [ -d /proc/$PID ]; do sleep 1; done
done
wait; echo CHAIN_UTIL3_DONE
