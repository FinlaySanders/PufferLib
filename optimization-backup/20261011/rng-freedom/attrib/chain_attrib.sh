#!/bin/bash
H=/puffertank/experiments/nethack-24h-20261009; P=/puffertank/experiments/nethack-rng-freedom-20261011
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 campaign_ablate.py ablate_attrib.json > $P/attrib/campaign_attrib.log 2>&1
python3 - <<'PY2'
import json,re,subprocess
H='/puffertank/experiments/nethack-24h-20261009/'
spec=json.load(open(H+'ablate_attrib.json'))
for a in spec:
    ag=[x for x in a['args'] if x.startswith('--agents=')][0].split('=')[1]; hz=[x for x in a['args'] if x.startswith('--horizon=')][0].split('=')[1]
    warm=str(32*262144) if int(ag)*int(hz)==262144 else str(16*524288)
    try: out=subprocess.run(['python3',H+'sps_from_log.py',H+f"runs/{a['label']}/run.log",ag,hz,warm],capture_output=True,text=True).stdout.strip().split('\n')[-1]
    except Exception as e: out=str(e)
    print(f"{a['label']:28s} {out}",flush=True)
PY2
echo "CHAIN_ATTRIB_DONE $(date -u +%T)"
