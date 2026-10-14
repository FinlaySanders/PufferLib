#!/bin/bash
# Stage 3: trainer build with the candidate C header (sched_v13), then the trainer A/B over engines (5M/2048 scheduler config).
N=/puffertank/experiments/nethack-engine-lines-20261014; X=/puffertank/experiments/nethack-scheduler-20261012; T=$X/trainer; L=$N/stage3.log
echo "stage3 waiting $(date -u +%T)" > $L
while ! grep -q NATIVE_SERIES_DONE $N/stage1.log 2>/dev/null; do sleep 10; done
H=$T/source/ocean/nethack/nethack.h; cp $H $N/headers/trainer_header_before_v13.h
python3 $N/apply_C.py $H >> $L 2>&1
(cd $T && python3 build.py sched_v13 > $N/build_v13.out 2>&1; echo "v13 build rc=$? $(date -u +%T)" >> $L)
sha256sum $H >> $L; cp $N/headers/trainer_header_before_v13.h $H; echo "trainer header restored: $(sha256sum $H | cut -c1-16)" >> $L
ln -sfn $T/binaries/sched_v13 /puffertank/experiments/nethack-24h-20261009/binaries/sched_v13
while ! grep -q STAGE2_DONE $N/stage2.log 2>/dev/null; do sleep 10; done
python3 - <<'PY'
import json
N='/puffertank/experiments/nethack-engine-lines-20261014'; X='/puffertank/experiments/nethack-scheduler-20261012'
ab=json.load(open(f'{X}/trainer/ab_tpause.json')); base=[a for a in ab if a['label']=='tp_spin_a'][0]
libs={'base':'/puffertank/experiments/nethack-compact-state-20261008/engines/tile_signed_pgo/build','selA':f'{N}/engines/selA/build','selB':f'{N}/engines/selB/build'}
def arm(label,lib,binary):
    a=json.loads(json.dumps(base)); a['label']=label; a['binary']=binary; a['env']['LD_LIBRARY_PATH']=libs[lib]; return a
arms=[]
for r in 'ab': arms+=[arm(f'eng_base_{r}','base','sched_v12'),arm(f'eng_selA_{r}','selA','sched_v12'),arm(f'eng_selB_{r}','selB','sched_v12'),arm(f'eng_selBC_{r}','selB','sched_v13')]
json.dump(arms,open(f'{N}/ab_engines.json','w'),indent=1); print([a['label'] for a in arms])
PY
rm -f $N/ab_engines.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $N/ab_engines.json > $N/ab_engines.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $L)
grep -E '^DONE' $N/ab_engines.log >> $L
echo "STAGE3_DONE $(date -u +%T)" >> $L
