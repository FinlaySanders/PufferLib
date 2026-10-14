#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/stageB/run.log; echo "stageB start $(date -u +%T)" > $G
cd /puffertank/experiments/nethack-24h-20261009 && rm -rf runs/prof_sched_v15 && bash -c "$(cat $L/stageB/prof_cmd.txt)" > $L/stageB/prof.log 2>&1; echo "profile rc=$? $(date -u +%T) $(ls runs/prof_sched_v15 | tr '\n' ' ')" >> $G
rm -f $L/ab_stageB.results.json $L/stageB/dump_*.slot*
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_stageB.json > $L/ab_stageB.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
R=/puffertank/experiments/nethack-24h-20261009/runs
python3 - >> $G <<'PY'
import hashlib
R='/puffertank/experiments/nethack-24h-20261009/runs'
for lab in ['sB_live_AB0','sB_live_AB0B1']:
    try: t=open(f'{R}/{lab}/run.log',errors='replace').read()
    except FileNotFoundError: print(lab,'missing'); continue
    lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
    print(lab, len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '| first differing epoch vs base digest run: n/a')
PY
for lab in sB_fast_off sB_fast_AB0 sB_fast_AB0B1 sB_fast_AB0B1_adapt sB_fast_off_b; do
  r=$R/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_stageB.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'cap_mean=[^ ]+|rt_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+' | tr '\n' ' ') | $(grep SCHED_GRAPH $r | head -1)" >> $G
done
python3 - >> $G <<'PY'
# numerics: compare logprob/value of the first 64 forwards per slot, AB0 vs AB0B1 (same recorded actions, same rows)
import glob, collections
L='/puffertank/experiments/nethack-latency-20261014/stageB'
def load(tag):
    d={}
    for p in glob.glob(f'{L}/dump_{tag}.slot*'):
        s=p.split('slot')[-1]
        for ln in open(p):
            f,r,a,lp,v=ln.split(); d[(s,int(f),int(r))]=(int(a),float(lp),float(v))
    return d
a=load('AB0'); b=load('AB0B1'); common=[k for k in a if k in b and a[k][0]==b[k][0]]
dlp=[abs(a[k][1]-b[k][1]) for k in common]; dv=[abs(a[k][2]-b[k][2]) for k in common]
import statistics
if common:
    print(f'NUMERICS rows={len(common)} agents-match={sum(1 for k in common)} | dlogprob max={max(dlp):.4g} mean={statistics.mean(dlp):.4g} frac>1e-3={sum(x>1e-3 for x in dlp)/len(dlp):.4f} | dvalue max={max(dv):.4g} mean={statistics.mean(dv):.4g}')
    ref=[abs(a[k][1]) for k in common]; print(f'   |logprob| mean={statistics.mean(ref):.4g}; |value| mean={statistics.mean(abs(a[k][2]) for k in common):.4g}')
else: print('NUMERICS: no common rows', len(a), len(b))
PY
echo "STAGEB_DONE $(date -u +%T)" >> $G
