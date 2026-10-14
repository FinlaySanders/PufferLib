#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/stageB/run3.log; echo "stageD start $(date -u +%T)" > $G
rm -f $L/ab_stageD.results.json $L/stageB/dump18_*.slot*
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/ab_stageD.json > $L/ab_stageD.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
R=/puffertank/experiments/nethack-24h-20261009/runs
python3 - >> $G <<'PY'
import hashlib
R='/puffertank/experiments/nethack-24h-20261009/runs'
for lab in ['sD_live_AB0','sD_live_all']:
    try: t=open(f'{R}/{lab}/run.log',errors='replace').read()
    except FileNotFoundError: print(lab,'missing'); continue
    lines=[l.strip() for l in t.splitlines() if l.startswith('LIVE_PROOF')]
    g=[l for l in t.splitlines() if l.startswith('SCHED_GRAPH')]
    print(lab, len(lines), 'epochs digest', hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], '(exact target 31e2e3deae720ef4) | graph', g[:1])
PY
for lab in sD_fast_off sD_fast_AB0 sD_fast_all sD_fast_all_adapt sD_fast_all_cap6 sD_fast_off_b; do
  r=$R/$lab/run.log
  echo "ARM $lab $(grep -E '^DONE '"$lab"' ' $L/ab_stageD.log | grep -oE 'sps [0-9]+|rc [0-9]+' | tr '\n' ' ') | $(grep SCHED_INFER $r | tail -1 | grep -oE 'rows_per_forward=[^ ]+|forward_us=[^ ]+' | tr '\n' ' ') | $(grep SCHED_STATS $r | tail -1 | grep -oE 'cap_mean=[^ ]+|rt_us=[^ ]+|hot_set_mean=[^ ]+|us_per_step=[^ ]+|borrow_pct=[^ ]+' | tr '\n' ' ') | $(grep SCHED_GRAPH $r | head -1)" >> $G
done
python3 - >> $G <<'PY'
import glob, statistics
L='/puffertank/experiments/nethack-latency-20261014/stageB'
def load(tag):
    d={}
    for p in glob.glob(f'{L}/dump18_{tag}.slot*'):
        for ln in open(p):
            f,r,a,tt,lp,v=ln.split(); d[(int(a),int(tt))]=(float(lp),float(v))
    return d
a=load('AB0'); b=load('all'); common=[k for k in a if k in b]
if common:
    dlp=[abs(a[k][0]-b[k][0]) for k in common]; dv=[abs(a[k][1]-b[k][1]) for k in common]
    print(f'NUMERICS tensor-core GEMM vs cuBLASLt (same agent, same step): rows={len(common)} of {len(a)}/{len(b)} | dlogprob max={max(dlp):.4g} mean={statistics.mean(dlp):.4g} frac>1e-2={sum(x>1e-2 for x in dlp)/len(dlp):.4f} frac>1e-1={sum(x>1e-1 for x in dlp)/len(dlp):.4f} | dvalue max={max(dv):.4g} mean={statistics.mean(dv):.4g} | |lp| mean={statistics.mean(abs(a[k][0]) for k in common):.4g} |v| mean={statistics.mean(abs(a[k][1]) for k in common):.4g}')
else: print('NUMERICS: no common (agent, step) rows', len(a), len(b))
PY
echo "STAGED_DONE $(date -u +%T)" >> $G
