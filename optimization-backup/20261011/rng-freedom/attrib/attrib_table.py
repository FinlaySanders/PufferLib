# Attribution table from the cumulative ladder: per regime, SPS at each step, increment over the previous step, share of total gain.
import json, re, subprocess, sys
H='/puffertank/experiments/nethack-24h-20261009/'
spec=json.load(open(H+'ablate_attrib.json'))
steps=['L0_alloff','L1_engine','L2_gpukernels','L3_lanes4','L4_gradoverlap','L5_prio_block','L6_pool24pin','L7_cohort']
names={'L0_alloff':'stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers','L1_engine':'+ engine mt7 (bit-exact ladder, PGO)','L2_gpukernels':'+ GPU fast kernels + entity fusions','L3_lanes4':'+ Muon 4 lanes','L4_gradoverlap':'+ gradient overlap, 32 connections','L5_prio_block':'+ inference priority, blocking waits','L6_pool24pin':'+ pool 24 workers, pinned','L7_cohort':'+ cohort 16/32 x 128, 4 active, 64 steps'}
def sps(label,ag,hz):
    warm=str(32*262144) if ag*hz==262144 else str(16*524288)
    r=subprocess.run(['python3',H+'sps_from_log.py',H+f'runs/{label}/run.log',str(ag),str(hz),warm],capture_output=True,text=True).stdout
    m=re.search(r'sps=(\d+)',r); return int(m.group(1)) if m else None
regs={}
for a in spec:
    reg=a['label'].split('_')[1]; ag=int([x for x in a['args'] if x.startswith('--agents=')][0].split('=')[1]); hz=int([x for x in a['args'] if x.startswith('--horizon=')][0].split('=')[1])
    regs.setdefault(reg,{})[a['label'].split('_',2)[2]]=sps(a['label'],ag,hz)
for reg,d in regs.items():
    ladder=[(s,d[s]) for s in steps if s in d and d[s]]
    if not ladder: print(reg,'no data'); continue
    base=ladder[0][1]; top=ladder[-1][1]; ctrl=d.get('ctrl_a')
    print(f"\n## {reg}: {base:,} -> {top:,} ({top/base:.2f}x); full-stack control before the ladder {ctrl:,} (drift {100*(top/ctrl-1):+.1f}%)" if ctrl else f"\n## {reg}")
    print(f"  {'step':14s} {'SPS':>9s} {'delta':>9s} {'pct':>7s} {'share':>6s}  component")
    prev=None
    for s,v in ladder:
        if prev is None: print(f"  {s:14s} {v:9,} {'':>9s} {'':>7s} {'':>6s}  {names[s]}")
        else: print(f"  {s:14s} {v:9,} {v-prev:+9,} {100*(v/prev-1):+6.1f}% {100*(v-prev)/(top-base):5.0f}%  {names[s]}")
        prev=v

# second ordering at 15M/2048: scheduling before the GPU items
spec2=json.load(open(H+'ablate_attrib2.json'))
names2={'M1_engine':'stock + engine','M2_sched':'+ scheduling block (priority, waits, pool 24 pinned, cohort)','M3_gpukernels':'+ GPU fast kernels + entity fusions','M4_lanes4':'+ Muon 4 lanes','M5_gradoverlap':'+ gradient overlap, 32 connections','ctrl_b':'full stack control after'}
d2={a['label'].split('_',2)[2]:sps(a['label'],2048,128) for a in spec2}
base=regs['15m2k']['L0_alloff']; prev=base
print(f"\n## 15m2k, second ordering (scheduling before GPU); baseline stock {base:,}")
for s in ['M1_engine','M2_sched','M3_gpukernels','M4_lanes4','M5_gradoverlap','ctrl_b']:
    v=d2.get(s)
    if v: print(f"  {s:14s} {v:9,} {v-prev:+9,} {100*(v/prev-1):+6.1f}%  {names2[s]}"); prev=v
