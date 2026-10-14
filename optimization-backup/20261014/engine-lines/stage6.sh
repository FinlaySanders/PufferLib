#!/bin/bash
# Stage 6 (after stage 5): live-learning proof across engines — weights updating, live sampled actions, 150 epochs, 2048 agents, 4 buffers;
# the per-epoch observation hashes (PUF_LIVE_PROOF) must be identical for base / selD / selD + C header.
N=/puffertank/experiments/nethack-engine-lines-20261014; X=/puffertank/experiments/nethack-scheduler-20261012; L=$N/stage6.log
echo "stage6 waiting $(date -u +%T)" > $L
while ! grep -q STAGE5_DONE $N/stage5.log 2>/dev/null; do sleep 15; done
ENG=selD; [ -f $N/engines/selD/build/libnethack.so ] && grep -q 'HASHES lines_selD 16777216 0' $N/stage5.log || ENG=selA
echo "live proof engine: $ENG" >> $L
python3 - $ENG <<'PY'
import json,sys
N='/puffertank/experiments/nethack-engine-lines-20261014'; X='/puffertank/experiments/nethack-scheduler-20261012'; eng=sys.argv[1]
base=[a for a in json.load(open(f'{X}/overnight/ab_livelearn.json')) if a['label']=='ll_sched'][0]
libs={'base':'/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build',eng:f'{N}/engines/{eng}/build'}
def arm(label,lib,binary):
    a=json.loads(json.dumps(base)); a['label']=label; a['binary']=binary; a['env']['LD_LIBRARY_PATH']=libs[lib]; return a
arms=[arm('live_eng_base','base','sched_v12'),arm(f'live_eng_{eng}',eng,'sched_v12'),arm(f'live_eng_{eng}_C',eng,'sched_v13')]
json.dump(arms,open(f'{N}/ab_live_engines.json','w'),indent=1); print([a['label'] for a in arms])
PY
rm -f $N/ab_live_engines.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $N/ab_live_engines.json > $N/ab_live_engines.log 2>&1; echo "live campaign rc=$? $(date -u +%T)" >> $L)
grep -E '^DONE' $N/ab_live_engines.log >> $L
python3 - $ENG <<'PY'
import re,sys,hashlib
N='/puffertank/experiments/nethack-engine-lines-20261014'; eng=sys.argv[1]
hs={}
for lab in ['live_eng_base',f'live_eng_{eng}',f'live_eng_{eng}_C']:
    try: t=open(f'/puffertank/experiments/nethack-24h-20261009/runs/{lab}/run.log',errors='replace').read()
    except FileNotFoundError: print(lab,'missing'); continue
    lines=[l for l in t.splitlines() if l.startswith('LIVE_PROOF')]
    hs[lab]=lines; print(lab, len(lines), 'LIVE_PROOF lines, digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '| last:', lines[-1][:90] if lines else '-')
ref=hs.get('live_eng_base')
for lab,l in hs.items():
    if lab!='live_eng_base': print('IDENTICAL to base' if l==ref and l else 'DIFFERENT from base', lab)
PY
echo "STAGE6_DONE $(date -u +%T)" >> $L
