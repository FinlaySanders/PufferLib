#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; X=/puffertank/experiments/nethack-scheduler-20261012; G=$L/stageB/run2.log; echo "stageC waiting $(date -u +%T)" > $G
while ! grep -q STAGEB_DONE $L/stageB/run.log 2>/dev/null; do sleep 15; done
(cd $X/trainer && python3 build.py sched_v17 > $L/stageB/build_v17.out 2>&1; echo "v17 build rc=$? $(date -u +%T)" >> $G)
grep -n ' error' $X/trainer/sched_v17-build.log | head -5 >> $G
[ -f $X/trainer/binaries/sched_v17 ] || { echo "NO BINARY" >> $G; echo "STAGEC_DONE" >> $G; exit 1; }
ln -sfn $X/trainer/binaries/sched_v17 /puffertank/experiments/nethack-24h-20261009/binaries/sched_v17
rm -f $L/ab_stageC.results.json $L/stageB/dump17_*.slot*
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_stageC.json > $L/ab_stageC.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
R=/puffertank/experiments/nethack-24h-20261009/runs
python3 - >> $G <<'PY'
import hashlib
R='/puffertank/experiments/nethack-24h-20261009/runs'
for lab in ['sC_live_AB0','sC_live_all']:
    try: t=open(f'{R}/{lab}/run.log',errors='replace').read()
    except FileNotFoundError: print(lab,'missing'); continue
    lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
    g=[l for l in t.splitlines() if l.startswith('SCHED_GRAPH')]
    print(lab, len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '| graph', g[:1])
PY
for lab in sC_fast_off sC_fast_AB0 sC_fast_all sC_fast_all_adapt sC_fast_all_cap6 sC_fast_off_b; do
  r=$R/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_stageC.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'cap_mean=[^ ]+|rt_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+|borrow_pct=[^ ]+' | tr '\n' ' ') | $(grep SCHED_GRAPH $r | head -1)" >> $G
done
python3 - >> $G <<'PY'
import glob, statistics
L='/puffertank/experiments/nethack-latency-20261014/stageB'
def load(tag):
    d={}
    for p in glob.glob(f'{L}/dump17_{tag}.slot*'):
        s=p.split('slot')[-1]
        for ln in open(p):
            f,r,a,lp,v=ln.split(); d[(s,int(f),int(r))]=(int(a),float(lp),float(v))
    return d
a=load('AB0'); b=load('all'); common=[k for k in a if k in b and a[k][0]==b[k][0]]
if common:
    dlp=[abs(a[k][1]-b[k][1]) for k in common]; dv=[abs(a[k][2]-b[k][2]) for k in common]
    print(f'NUMERICS all-vs-AB0 rows={len(common)} | dlogprob max={max(dlp):.4g} mean={statistics.mean(dlp):.4g} frac>1e-2={sum(x>1e-2 for x in dlp)/len(dlp):.4f} | dvalue max={max(dv):.4g} mean={statistics.mean(dv):.4g} | |lp| mean={statistics.mean(abs(a[k][1]) for k in common):.4g} |v| mean={statistics.mean(abs(a[k][2]) for k in common):.4g}')
else: print('NUMERICS: no common rows', len(a), len(b))
PY
echo "STAGEC_DONE $(date -u +%T)" >> $G
