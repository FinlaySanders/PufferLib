#!/bin/bash
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; H=/puffertank/experiments/nethack-24h-20261009; cd $H
while ! grep -q "CHAIN_4096_DONE" $S/chain_4096.log; do sleep 5; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
python3 - <<'PY'
import json,shutil,pathlib
f=pathlib.Path('ablate_4096.results.json'); r=[x for x in json.load(f.open()) if not x['label'].endswith('_coh')]; f.write_text(json.dumps(r,indent=2))
for L in ('a4k5m_coh','a4k15m_coh'): shutil.rmtree('runs/'+L,ignore_errors=True)
print('purged coh arms')
PY
python3 campaign_ablate.py ablate_4096.json
for L in a4k5m_ctrl a4k5m_coh a4k15m_ctrl a4k15m_coh; do printf "%-12s " $L; python3 sps_from_log.py runs/$L/run.log 4096 2>&1 | tail -1; done
echo CHAIN_4096_FIX_DONE
