#!/bin/bash
# ini-key validation (3 arms on the patched binary) with the per-thread utilisation sampler on the control and the env-var cohort arm
H=/puffertank/experiments/nethack-24h-20261009; cd $H
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 campaign_ablate.py ablate_ini.json &
for L in ini5_ctrl:36:66 ini5_env:30:55 ini5_keys:30:55; do IFS=: read NAME T1 T2 <<<"$L"
  while ! PID=$(pgrep -f "^/puffertank/experiments/nethack-24h-20261009/binaries/cohort_ini .*" | head -1) || [ -z "$PID" ] || ! grep -q "$NAME" /proc/$PID/cmdline 2>/dev/null; do sleep 1; done
  echo "ATTACH $NAME pid=$PID $(date -u +%T)"
  ./thread_util.sh $PID $T1 $T2 | sed "s/^/$NAME: /"
  while [ -d /proc/$PID ]; do sleep 1; done
done
wait
for L in ini5_ctrl ini5_env ini5_keys; do printf "%-10s sps=%s proofs=%s\n" $L "$(python3 -c "import json;print(round(json.load(open('runs/$L/result.json')).get('sps',0)))")" "$(grep -c BATCH_PROOF runs/$L/run.log)"; done
if cmp -s <(grep BATCH_PROOF runs/ini5_env/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/ini5_keys/run.log | sed 's/epoch=[0-9]* //'); then echo "PROOF env-vars vs ini-keys: IDENTICAL ($(grep -c BATCH_PROOF runs/ini5_env/run.log) lines)"; else echo "PROOF env-vars vs ini-keys: DIFFER"; diff <(grep BATCH_PROOF runs/ini5_env/run.log) <(grep BATCH_PROOF runs/ini5_keys/run.log) | head -4; fi
grep -h "cohort\|COHORT" runs/ini5_keys/run.log | head -3
echo CHAIN_VALIDATE3_DONE
