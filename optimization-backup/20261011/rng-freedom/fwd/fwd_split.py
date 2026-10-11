# Split each buffer cycle (sample_logits -> sample_logits on one stream) at its largest gap: forward proper vs env phase.
import sqlite3, sys, statistics, collections
db=sqlite3.connect(sys.argv[1]); cur=db.cursor(); label=sys.argv[2]
names={i:s for i,s in cur.execute("SELECT id,value FROM StringIds")}
short=lambda i: names[i].split('(')[0].replace('void ','').split('<')[0][:40]
muon=set(s for (s,) in cur.execute("SELECT DISTINCT k.streamId FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds n ON k.shortName=n.id WHERE n.value LIKE 'muon%'"))
streams=[s for (s,) in cur.execute("SELECT DISTINCT streamId FROM CUPTI_ACTIVITY_KIND_KERNEL") if s not in muon]
fwd=[]; env=[]; cyc=[]; nk=[]; firsts=collections.Counter(); busy=[]; example=None
for s in streams:
    ks=list(cur.execute("SELECT start,end,shortName FROM CUPTI_ACTIVITY_KIND_KERNEL WHERE streamId=? ORDER BY start",(s,)))
    cuts=[i for i,k in enumerate(ks) if 'sample_logits' in names[k[2]]]
    for a,b in zip(cuts[:-1],cuts[1:]):
        seq=ks[a+1:b+1]
        if len(seq)<10: continue
        gaps=[(seq[i][0]-seq[i-1][1],i) for i in range(1,len(seq))]; g,i=max(gaps)
        f=seq[i:]; fwd.append((f[-1][1]-f[0][0])/1e3); env.append(g/1e3); cyc.append((seq[-1][1]-seq[0][0])/1e3); nk.append(len(f))
        busy.append(sum(e-st for st,e,_ in f)/1e3); firsts[short(f[0][2])]+=1
        if example is None and len(fwd)>200: example=f
n=len(fwd); med=lambda v: statistics.median(v)
print(f"{label}: cycles {n}; forward proper: median wall {med(fwd):.0f} us (p10 {sorted(fwd)[n//10]:.0f}, p90 {sorted(fwd)[9*n//10]:.0f}), kernels {med(nk):.0f}, busy {med(busy):.0f} us; env phase gap median {med(env):.0f} us; cycle median {med(cyc):.0f} us")
print("  forward starts with:", firsts.most_common(3))
prev=None; out=[]
for st,e,nm in example:
    gap=(st-prev)/1e3 if prev else 0; prev=e; out.append(f"{short(nm)}:{(e-st)/1e3:.0f}{'+%.0f'%gap if gap>=5 else ''}")
print("  example forward (kernel:us[+gap before]):", ' '.join(out))
