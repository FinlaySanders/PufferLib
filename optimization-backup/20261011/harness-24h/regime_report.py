# Consolidated tables from every ablate_*.results.json; writes REGIME_RESULTS.md next to PROGRAM.md.
import json,statistics
from pathlib import Path
R=Path(__file__).resolve().parent; OUT=Path('/puffertank/experiments/nethack-engine-scaling-20261010/REGIME_RESULTS.md')
def load(tag):
    p=R/f'ablate_{tag}.results.json'
    return json.load(open(p)) if p.exists() else []
def start_of(r): return int([a for a in r['job']['args'] if a.startswith('--start=')][0].split('=')[1])
def avg(r,k):
    m=[e for e in r['epochs'] if e['epoch']>=start_of(r)]; return statistics.mean(e[k] for e in m)*1000
L=[]; P=L.append
P('# NetHack throughput regime results — 10 October 2026\n')
P('Full stack = attribution_v37 with retained engine, GPU fast kernels, entity fusions, 4 Muon lanes, gradient overlap + 32 connections, inference priority, blocking waits, 32 workers. Frozen-actor recorded-action replay (mature games), batch 262,144, minibatch 4096, replay 1.78 unless stated. Fast protocol: 12 measured epochs after the mature plateau (512 agents: epochs 16-27; 2048: 32-43). Long window (15m512 only): epochs 24-62. Controls bracket every set; "drift" = closing vs opening control.\n')
ARMS={'full_a':'full stack (control a)','all_off':'everything off (stock engine, no GPU flags, 1 lane, overlap off, 8 conn, priority off)','eng_stock':'engine -> stock fast-nle (vendored HEAD)','eng_sept14':'engine -> September engine14','eng_precompact':'engine -> pre-compact-state (persist)','gpufast_off':'GPU fast kernels off','entity_off':'entity fusions off','lanes1':'Muon lanes 4 -> 1','gradpipe_off':'gradient overlap off + 8 connections','prio_off':'inference priority off','wait_off':'blocking wait / finish sleep off','workers16':'workers 32 -> 16','full_b':'full stack (control b)'}
for tag,title in [('15m512','15M model, 512 agents, LONG window'),('fast15m512','15M, 512 agents'),('fast5m512','5M, 512 agents'),('fast15m2048','15M, 2048 agents'),('fast5m2048','5M, 2048 agents')]:
    rs=load(tag)
    if not rs: continue
    by={r['label'].split('_',1)[1]:r for r in rs if 'sps' in r}
    ctrl=[by[k]['sps'] for k in ('full_a','full_b') if k in by]; ref=statistics.mean(ctrl)
    P(f'\n## Leave-one-out: {title}\n\nFull-stack mean {ref:,.0f} SPS (controls {", ".join(f"{c:,.0f}" for c in ctrl)}, drift {(ctrl[-1]/ctrl[0]-1)*100:+.2f}%).\n')
    P('| Arm | SPS | vs full | epoch ms | rollout tail ms | PPO tail ms |\n|---|---:|---:|---:|---:|---:|')
    for k,r in by.items():
        P(f"| {ARMS.get(k,k)} | {r['sps']:,.0f} | {(r['sps']/ref-1)*100:+.2f}% | {avg(r,'seconds'):.0f} | {avg(r,'rollout_tail'):.0f} | {avg(r,'ppo_tail'):.0f} |")
# scaling
rs=load('scale')
if rs:
    P('\n## Agent-count scaling at constant batch (full stack, matched game age = 4096 recorded steps per env)\n')
    P('| Model | Agents x horizon | SPS | epoch ms | PPO est ms | rollout tail | PPO tail |\n|---|---|---:|---:|---:|---:|---:|')
    by={}
    for r in rs:
        if 'sps' in r: _,w,a,_=r['label'].split('_'); by.setdefault((w,a),[]).append(r)
    for (w,a),f in [(('w1024','a2048'),'fast15m2048'),(('w512','a2048'),'fast5m2048')]:
        by[(w,a)]=[r for r in load(f) if r['label'].endswith(('full_a','full_b'))]
    for w in ('w1024','w512'):
        for a in ('a512','a1024','a2048','a4096'):
            rr=by.get((w,a))
            if not rr: continue
            sps=statistics.mean(r['sps'] for r in rr); ep=statistics.mean(avg(r,'seconds') for r in rr); rt=statistics.mean(avg(r,'rollout_tail') for r in rr); pt=statistics.mean(avg(r,'ppo_tail') for r in rr)
            h={'a512':512,'a1024':256,'a2048':128,'a4096':64}[a]
            P(f"| {'15M' if w=='w1024' else '5M'} | {a[1:]} x {h} | {sps:,.0f} | {ep:.0f} | {ep-rt:.0f} | {rt:.0f} | {pt:.0f} |")
def simple(tag,title,strip,ctrl_prefixes):
    rs=load(tag)
    if not rs: return
    P(f'\n## {title}\n')
    groups={}
    for r in rs:
        t,arm=r['label'].replace(strip,'').split('_',1); groups.setdefault(t,[]).append((arm,r))
    for t,items in groups.items():
        ctrl=[r['sps'] for a,r in items if a.startswith(ctrl_prefixes) and 'sps' in r]; ref=statistics.mean(ctrl)
        P(f'\n**{t}** — controls {", ".join(f"{c:,.0f}" for c in ctrl)} (drift {(ctrl[-1]/ctrl[0]-1)*100:+.2f}%)\n')
        P('| Arm | SPS | vs control | epoch ms | PPO est ms | rollout tail | PPO tail |\n|---|---:|---:|---:|---:|---:|---:|')
        for a,r in items:
            if 'sps' not in r: P(f'| {a} | failed | | | | | |'); continue
            P(f"| {a} | {r['sps']:,.0f} | {(r['sps']/ref-1)*100:+.2f}% | {avg(r,'seconds'):.0f} | {avg(r,'seconds')-avg(r,'rollout_tail'):.0f} | {avg(r,'rollout_tail'):.0f} | {avg(r,'ppo_tail'):.0f} |")
simple('muonfused15m512','Fused small-matrix Muon (PUF_MUON_FUSED_SMALL=64, 21 matrices), 15M/512','ablmuonfused',('base',))
simple('phasecfg','Phase-dependent GPU scheduling, collection-bound regimes','ablphase',('full',))
simple('minibatch','Minibatch size (replay 1.78 fixed; updates/batch 113 -> 56 -> 28 -> 14)','ablmb',('mb4096',))
simple('best15m512','Best known 15M/512 combination: minibatch 8192 + fused Muon','ablbest15m512',('mb8192_a','mb8192_b'))
simple('engines2048','Parked engine patches in the collection-bound full pipeline (controls = PGO retained; see non-PGO control below)','ableng',('full',))
simple('engines2048_ctrl','Non-PGO retained engine control (fair baseline for ordinary-LTO candidates; PGO itself = +4.9%)','ableng',('nonpgo',))
simple('incpack','Candidate A: incremental glyph export (engine incexport2) and incremental packer (trainer incpack_v38), vs non-PGO retained','ablinc',('ctrl',))
simple('incstack','Stacked candidate: incstack engine (incremental export + liquid + immutable), with and without the packer trainer, vs non-PGO retained','ablstack',('ctrl',))
simple('landing','LANDING comparison: retained PGO engine + v37 trainer (current full stack) vs incstack PGO engine + incpack_v38 trainer','abllanding',('ctrl',))
simple('landing2','LANDING (final, fixed export): retained PGO + v37 vs incstack2 PGO + incpack_v38 — all gates clean','abllanding2',('ctrl',))
simple('pin','Worker pinning (PUF_CPU_AFFINITY=2, one worker per logical CPU) in the full pipeline, incpack_v39 vs incpack_v38, both on incstack2 PGO','ablpin',('ctrl',))
OUT.write_text('\n'.join(L)+'\n'); print('wrote',OUT,len(L),'lines')
