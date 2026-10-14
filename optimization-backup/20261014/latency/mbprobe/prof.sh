#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; cd /puffertank/experiments/nethack-24h-20261009 && rm -rf runs/prof_mb32k && bash -c "$(cat $L/mbprobe/prof_cmd.txt)" > $L/mbprobe/prof.log 2>&1; echo "profile rc=$? $(date -u +%T)" >> $L/mbprobe/prof.log
python3 - >> $L/mbprobe/prof.log <<'PY'
import sqlite3,collections
p='/puffertank/experiments/nethack-24h-20261009/runs/prof_mb32k/timeline.sqlite'; c=sqlite3.connect(p)
sid=dict(c.execute("select id,value from StringIds").fetchall())
ks=c.execute("select start,end,demangledName,streamId from CUPTI_ACTIVITY_KIND_KERNEL").fetchall()
name=lambda k: sid[k[2]].split('(')[0].split('<')[0][-46:]
# pool path: inference kernels run on the per-buffer streams; identify them by the sampler kernel
inf={k[3] for k in ks if name(k)=='sample_logits_heads'}
tr=[k for k in ks if k[3] not in inf]; epochs=12
agg=collections.defaultdict(lambda:[0,0.0])
for k in tr: agg[name(k)][0]+=1; agg[name(k)][1]+=(k[1]-k[0])/1e3
tot=sum(v[1] for v in agg.values()); print(f'TRAINING kernels at mb 32768: {tot/epochs/1e3:.0f} ms/epoch summed, {len(tr)/epochs:.0f} kernels/epoch; inference streams {sorted(inf)}')
for nm,(cnt,us) in sorted(agg.items(), key=lambda x:-x[1][1])[:26]: print(f'{us/epochs/1e3:7.1f} ms/epoch  x{cnt/epochs:6.0f}  {us/cnt:7.1f} us each  {nm}')
# training-phase wall: NVTX train range
tr_rng=c.execute("select start,end from NVTX_EVENTS where text='train_forward_backward' order by start").fetchall()
if tr_rng: import statistics; print('train_forward_backward NVTX ranges:', len(tr_rng), 'mean', round(statistics.mean((e-s)/1e6 for s,e in tr_rng),1), 'ms')
PY
echo PROFMB_DONE >> $L/mbprobe/prof.log
