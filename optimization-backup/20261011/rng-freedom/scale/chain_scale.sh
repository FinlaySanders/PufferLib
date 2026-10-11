#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_scale.json > $P/scale/campaign_scale.log 2>&1
python3 - <<'PY2'
import json,re,subprocess
H='/puffertank/experiments/nethack-24h-20261009/'
for a in json.load(open(H+'ablate_scale.json')):
    ag=int([x for x in a['args'] if x.startswith('--agents=')][0].split('=')[1]); hz=int([x for x in a['args'] if x.startswith('--horizon=')][0].split('=')[1])
    warm=str(32*262144) if ag*hz<=262144 else str(16*524288)
    out=subprocess.run(['python3',H+'sps_from_log.py',H+f"runs/{a['label']}/run.log",str(ag),str(hz),warm],capture_output=True,text=True).stdout.strip().split('\n')[-1]
    perf=subprocess.run(['bash','-c',f"grep -h -o 'BATCH_PERF epoch=[0-9]* seconds=[0-9.]* rollout_tail=[0-9.]* ppo_tail=[0-9.]*' {H}runs/{a['label']}/run.log | tail -1"],capture_output=True,text=True).stdout.strip()
    print(f"{a['label']:36s} {out[:34]}  {perf[17:]}",flush=True)
PY2
echo "CHAIN_SCALE_DONE $(date -u +%T)"
