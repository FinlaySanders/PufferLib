#!/bin/bash
# cohort utilisation sample strictly inside the rollout phase (run ≈ 38 s incl. 4 s startup and ~2 s teardown): window 12-28 s
H=/puffertank/experiments/nethack-24h-20261009; cd $H
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 campaign_ablate.py ablate_util6.json &
NAME=util6_env
while ! PID=$(pgrep -f "^/puffertank/experiments/nethack-24h-20261009/binaries/cohort_ini .*" | head -1) || [ -z "$PID" ] || ! grep -q "$NAME" /proc/$PID/cmdline 2>/dev/null; do sleep 1; done
echo "ATTACH $NAME pid=$PID $(date -u +%T)"
./thread_util.sh $PID 12 28 | sed "s/^/$NAME: /"
wait; echo CHAIN_UTIL6_DONE
