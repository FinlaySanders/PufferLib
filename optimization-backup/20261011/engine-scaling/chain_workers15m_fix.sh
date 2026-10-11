#!/bin/bash
# re-run w15m_32 (killed by my cleanup pkill), then the three-way comparison
S=/tmp/claude-0/-puffertank-pufferlib/6445c370-8cc3-4880-b660-5f83a21b200b/scratchpad; H=/puffertank/experiments/nethack-24h-20261009
while ! grep -q "CHAIN_WORKERS15M_DONE" $S/chain_workers15m.log; do sleep 5; done
while nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -q .; do sleep 2; done
cd $H && python3 - <<'PY'
import json,shutil,pathlib
f=pathlib.Path('ablate_workers15m.results.json'); r=[x for x in json.load(f.open()) if x['label']!='w15m_32']; f.write_text(json.dumps(r,indent=2))
shutil.rmtree('runs/w15m_32',ignore_errors=True); print('purged w15m_32')
PY
python3 campaign_ablate.py ablate_workers15m.json
for L in w15m_32 w15m_24 w15m_20; do printf "%-8s sps=%s\n" $L "$(python3 -c "import json;print(round(json.load(open('runs/$L/result.json')).get('sps',0)))")"; done
for L in w15m_24 w15m_20; do cmp -s <(grep BATCH_PROOF runs/w15m_32/run.log | sed 's/epoch=[0-9]* //') <(grep BATCH_PROOF runs/$L/run.log | sed 's/epoch=[0-9]* //') && echo "PROOF $L: identical" || echo "PROOF $L: DIFFERS"; done
echo CHAIN_WORKERS15M_FIX_DONE
