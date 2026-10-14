#!/bin/bash
L=/puffertank/experiments/nethack-latency-20261014; G=$L/mbprobe/run.log; echo "mbprobe start $(date -u +%T)" > $G
rm -f $L/mbprobe/ab_mb.results.json
(cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py $L/mbprobe/ab_mb.json > $L/mbprobe/ab_mb.log 2>&1; echo "campaign rc=$? $(date -u +%T)" >> $G)
python3 - >> $G <<'PY'
import re, statistics, json
R='/puffertank/experiments/nethack-24h-20261009/runs'
for lab in ['mb_4096','mb_8192','mb_16384','mb_32768','mb_4096_rr1','mb_32768_rr1','mb_4096_b']:
    try: t=open(f'{R}/{lab}/run.log',errors='replace').read()
    except FileNotFoundError: print(lab,'missing'); continue
    train=[int(x) for x in re.findall(r'Train\s+(\d+)ms',t)]; model=[int(x) for x in re.findall(r'Model\s+(\d+)ms',t)]
    bp=[dict(re.findall(r'(\w+)=([\d.]+)',l)) for l in t.splitlines() if l.startswith('BATCH_PERF')]
    secs=[float(r['seconds']) for r in bp[32:43]]; upd=bp[-1].get('updates','?') if bp else '?'
    sps=re.findall(r'"sps": ([\d.]+)', open(f'{R}/{lab}/result.json').read()) if True else []
    print(f"{lab:14s} train_ms(last 10 epochs) mean={statistics.mean(train[-10:]) if train else 0:.0f} min={min(train[-10:]) if train else 0} | model_ms mean={statistics.mean(model[-10:]) if model else 0:.0f} | updates/epoch={upd} | epoch wall mean={statistics.mean(secs) if secs else 0:.3f}s | sps={sps[0] if sps else '?'}")
PY
echo "MBPROBE_DONE $(date -u +%T)" >> $G
