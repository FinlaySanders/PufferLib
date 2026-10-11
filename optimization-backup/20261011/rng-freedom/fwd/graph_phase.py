# Graph-mode trace: per-stream graph launches -> inference (many short) vs PPO (long) streams; durations and phase walls.
import sqlite3, sys, statistics, collections
db=sqlite3.connect(sys.argv[1]); cur=db.cursor(); label=sys.argv[2]
by=collections.defaultdict(list)
for s,st,e in cur.execute("SELECT streamId,start,end FROM CUPTI_ACTIVITY_KIND_GRAPH_TRACE"): by[s].append((st,e))
med={s:statistics.median(e-st for st,e in v)/1e3 for s,v in by.items()}
ppo=[s for s in by if med[s]>1500]; inf=[s for s in by if med[s]<=1500]
def union(iv):
    iv=sorted(iv); out=[]
    for s,e in iv:
        if out and s<=out[-1][1]: out[-1][1]=max(out[-1][1],e)
        else: out.append([s,e])
    return out
def phases(iv,gap): # merge launches separated by < gap ns into phases
    ph=[]
    for s,e in union(iv):
        if ph and s-ph[-1][1]<gap: ph[-1][1]=e
        else: ph.append([s,e])
    return ph
pi=[x for s in ppo for x in by[s]]; ii=[x for s in inf for x in by[s]]
pph=phases(pi,20e6); iph=phases(ii,20e6)
fwd=[(e-st)/1e3 for s in inf for st,e in by[s]]; pg=[(e-st)/1e3 for s in ppo for st,e in by[s]]
print(f"{label}: inference streams {len(inf)} graphs {len(fwd)}; PPO streams {len(ppo)} graphs {len(pg)}")
print(f"  forward graph wall us: median {statistics.median(fwd):.0f} p10 {sorted(fwd)[len(fwd)//10]:.0f} p90 {sorted(fwd)[9*len(fwd)//10]:.0f}")
print(f"  PPO graph wall us: median {statistics.median(pg):.0f}; PPO phases {len(pph)} mean {statistics.mean(e-s for s,e in pph)/1e9:.3f} s; rollout phases {len(iph)} mean {statistics.mean(e-s for s,e in iph)/1e9:.3f} s")
ov=0; i=j=0; a=union(pi); b=union(ii)
while i<len(a) and j<len(b):
    s=max(a[i][0],b[j][0]); e=min(a[i][1],b[j][1]); ov+=max(0,e-s)
    if a[i][1]<b[j][1]: i+=1
    else: j+=1
print(f"  PPO/inference graph overlap: {ov/1e9:.2f} s of PPO busy {sum(e-s for s,e in a)/1e9:.2f} s ({100*ov/max(1,sum(e-s for s,e in a)):.0f}%)")
