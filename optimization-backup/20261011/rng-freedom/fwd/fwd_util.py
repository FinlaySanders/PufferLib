# GPU utilisation by inference kernels during rollout phases, and launch structure (graph vs host launches), from an nsys sqlite.
import sqlite3, sys, collections
db=sqlite3.connect(sys.argv[1]); cur=db.cursor(); label=sys.argv[2]
names={i:s for i,s in cur.execute("SELECT id,value FROM StringIds")}
muon=set(s for (s,) in cur.execute("SELECT DISTINCT k.streamId FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds n ON k.shortName=n.id WHERE n.value LIKE 'muon%'"))
def union(iv):
    iv.sort(); out=[]; 
    for s,e in iv:
        if out and s<=out[-1][1]: out[-1][1]=max(out[-1][1],e)
        else: out.append([s,e])
    return out
ppo=union([[s,e] for s,e in cur.execute("SELECT start,end FROM CUPTI_ACTIVITY_KIND_KERNEL WHERE streamId IN (%s)"%','.join(map(str,muon)))])
# merge PPO intervals separated by <5 ms into phases
ph=[]; 
for s,e in ppo:
    if ph and s-ph[-1][1]<5e6: ph[-1][1]=e
    else: ph.append([s,e])
t0,t1=cur.execute("SELECT MIN(start),MAX(end) FROM CUPTI_ACTIVITY_KIND_KERNEL").fetchone()
roll=[]; prev=t0
for s,e in ph: 
    if s-prev>50e6: roll.append([prev,s])
    prev=e
if t1-prev>50e6: roll.append([prev,t1])
inf=union([[s,e] for s,e in cur.execute("SELECT start,end FROM CUPTI_ACTIVITY_KIND_KERNEL WHERE streamId NOT IN (%s)"%','.join(map(str,muon)))])
def overlap(a,b):
    i=j=0; tot=0
    while i<len(a) and j<len(b):
        s=max(a[i][0],b[j][0]); e=min(a[i][1],b[j][1])
        if e>s: tot+=e-s
        if a[i][1]<b[j][1]: i+=1
        else: j+=1
    return tot
rw=sum(e-s for s,e in roll); pw=sum(e-s for s,e in ph)
print(f"{label}: PPO phases {len(ph)} total {pw/1e9:.2f} s; rollout windows {len(roll)} total {rw/1e9:.2f} s")
print(f"  inference-kernel GPU busy during rollout: {100*overlap(inf,roll)/rw:.0f}%   (union of kernel intervals / rollout wall)")
# concurrency: average number of inference kernels running at once during rollout
ev=[]
for s,e in cur.execute("SELECT start,end FROM CUPTI_ACTIVITY_KIND_KERNEL WHERE streamId NOT IN (%s)"%','.join(map(str,muon))): ev.append((s,1)); ev.append((e,-1))
ev.sort(); n=0; last=ev[0][0]; hist=collections.Counter()
for t,d in ev:
    hist[n]+=t-last; n+=d; last=t
tot=sum(hist.values()); print("  concurrent inference kernels, time share:", {k:round(100*v/tot) for k,v in sorted(hist.items()) if 100*v/tot>=1})
# runtime API structure
api=collections.Counter()
for nm,c in cur.execute("SELECT nameId,COUNT(*) FROM CUPTI_ACTIVITY_KIND_RUNTIME GROUP BY nameId"): api[names[nm].split('_v')[0]]+=c
fw=cur.execute("SELECT COUNT(*) FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds n ON k.shortName=n.id WHERE n.value LIKE 'sample_logits%'").fetchone()[0]
print(f"  forwards {fw}; runtime API calls per forward:", {k:round(v/fw,1) for k,v in api.most_common(12)})
