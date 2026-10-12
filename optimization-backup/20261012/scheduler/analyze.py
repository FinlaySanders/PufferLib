#!/usr/bin/env python3
"""Render screens/summary.txt: per game count, every arm vs the latency-matched pool control; hash check; balance (wall/busy)."""
import re,sys,collections
path=sys.argv[1] if len(sys.argv)>1 else '/puffertank/experiments/nethack-scheduler-20261012/screens/summary.txt'
rows=collections.OrderedDict()
for line in open(path):
    m=re.match(r'^(\d+) (\S+) (.*)$',line.strip())
    if not m: continue
    N,tag,rest=int(m.group(1)),m.group(2),m.group(3)
    kv=dict(x.split('=',1) for x in rest.split() if '=' in x)
    rows.setdefault(N,collections.OrderedDict())[tag]=kv
def f(kv,k,d=None):
    try: return float(kv[k])
    except Exception: return d
for N,arms in rows.items():
    ref=next((a for a in arms if a.startswith('pool_f')),None)
    refhash=arms[ref]['obs'] if ref else None
    ctrl={'f0':f(arms.get('pool_f0',{}),'sps'),'f350':f(arms.get('pool_f350',{}),'sps'),'f800':f(arms.get('pool_f800',{}),'sps')}
    print(f"\n=== {N} games (24 workers pinned) — pool controls: F0 {ctrl['f0']:.0f}  F350 {ctrl['f350']:.0f}  F800 {ctrl['f800']:.0f}  hash {refhash}" if ctrl['f0'] else f"\n=== {N} games")
    print(f"{'arm':24s} {'wall SPS':>9s} {'vs ctrl':>8s} {'busy SPS':>9s} {'wall/busy':>9s} {'idle':>6s} {'bar':>6s} {'steals':>6s} {'splits':>6s} {'borrow%':>7s} hash")
    for tag,kv in arms.items():
        sps=f(kv,'sps'); 
        if sps is None: print(f"{tag:24s} (no result)"); continue
        if tag.startswith('l5m') or 'f350' in tag: c=ctrl['f350']
        elif tag.startswith('l15m') or 'f800' in tag: c=ctrl['f800']
        else: c=ctrl['f0']
        vs=f"{(sps/c-1)*100:+.1f}%" if c else ''
        b=f(kv,'busy_sps'); wb=f"{sps/b:.3f}" if b else ''
        idle=kv.get('idle_mean',kv.get('gpu_wait_mean','')); bar=kv.get('bar_mean',''); st=kv.get('steals',''); sp=kv.get('splits','')
        m=re.search(r'_c(\d+)',tag); C=int(m.group(1)) if m else 0; steps=4096 if N<=512 else 2048
        bo=f(kv,'borrows'); own=f"{100*bo*C/(N*steps):.1f}" if (bo is not None and C) else ''
        hs=kv.get('obs',''); flag='' if hs==refhash else '  <-- HASH DIFFERS'
        print(f"{tag:24s} {sps:9.0f} {vs:>8s} {(b or 0):9.0f} {wb:>9s} {str(idle)[:6]:>6s} {str(bar)[:6]:>6s} {st:>6s} {sp:>6s} {own:>7s} {hs}{flag}")
