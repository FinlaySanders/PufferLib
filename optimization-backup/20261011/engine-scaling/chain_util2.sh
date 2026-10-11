#!/bin/bash
# Re-run the cohort utilisation arm with the sampler attached to the trainer process itself (anchored match).
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad
cd /puffertank/experiments/nethack-24h-20261009
while pgrep -f "campaign_ablate[.]py ablate_util[.]json" >/dev/null; do sleep 3; done; echo "WAIT_UTIL1_DONE $(date -u +%T)"
python3 campaign_ablate.py ablate_util2.json &
while ! PID=$(pgrep -f "^/puffertank/experiments/nethack-24h-20261009/binaries/incpack_v39" | head -1) || [ -z "$PID" ]; do sleep 1; done
echo "ATTACH util5_b16c4s64_r2 pid=$PID $(date -u +%T) threads=$(ls /proc/$PID/task | wc -l)"
./thread_util.sh $PID 34 64 | sed 's/^/util5_b16c4s64_r2: /'
wait; echo CHAIN_UTIL2_DONE
