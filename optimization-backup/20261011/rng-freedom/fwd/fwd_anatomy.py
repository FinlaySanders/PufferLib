# Per-forward anatomy of the actor path from an nsys sqlite: forwards delimited by sample_logits_heads on each inference stream.
import sqlite3, sys, collections, statistics
db=sqlite3.connect(sys.argv[1]); cur=db.cursor(); label=sys.argv[2] if len(sys.argv)>2 else sys.argv[1]
names={i:s for i,s in cur.execute("SELECT id,value FROM StringIds")}
short=lambda i: names[i].split('(')[0].replace('void ','').split('<')[0][:48]
streams=[s for (s,) in cur.execute("SELECT DISTINCT streamId FROM CUPTI_ACTIVITY_KIND_KERNEL")]
muon=set(s for (s,) in cur.execute("SELECT DISTINCT k.streamId FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds n ON k.shortName=n.id WHERE n.value LIKE 'muon%'"))
inf=[s for s in streams if s not in muon]
fw=[]; per=collections.defaultdict(list); gaps_big=collections.Counter()
for s in inf:
    ks=list(cur.execute("SELECT start,end,shortName FROM CUPTI_ACTIVITY_KIND_KERNEL WHERE streamId=? ORDER BY start",(s,)))
    cuts=[i for i,k in enumerate(ks) if 'sample_logits' in names[k[2]]]
    if len(cuts)<3: continue
    for a,b in zip(cuts[:-1],cuts[1:]):
        seq=ks[a+1:b+1]; wall=(seq[-1][1]-seq[0][0])/1e3; busy=sum(e-st for st,e,_ in seq)/1e3
        fw.append((wall,busy,len(seq),s))
        prev=None
        for st,e,nm in seq:
            per[short(nm)].append((e-st)/1e3)
            if prev is not None and st-prev>20e3: gaps_big[short(nm)]+=1
            prev=e
if not fw: sys.exit('no forwards found')
n=len(fw); walls=sorted(w for w,_,_,_ in fw); busys=[b for _,b,_,_ in fw]
print(f"{label}: streams {inf} forwards {n}  kernels/forward {statistics.mean(k for _,_,k,_ in fw):.1f}")
print(f"  wall us: median {walls[n//2]:.0f} p10 {walls[n//10]:.0f} p90 {walls[9*n//10]:.0f} | busy us: mean {statistics.mean(busys):.0f} | gaps = wall-busy median {walls[n//2]-statistics.median(busys):.0f}")
rows=sorted(((sum(v)/n, len(v)/n, statistics.mean(v), k) for k,v in per.items()), reverse=True)
print("  per forward: total_us  count  mean_us  kernel")
for tot,cnt,mean,k in rows[:26]: print(f"    {tot:7.1f}  {cnt:5.1f}  {mean:6.1f}  {k}")
print("  kernels most often preceded by a >20 us gap:", gaps_big.most_common(6))
mc=list(cur.execute("SELECT copyKind,COUNT(*),AVG(end-start)/1e3,AVG(bytes) FROM CUPTI_ACTIVITY_KIND_MEMCPY WHERE streamId IN (%s) GROUP BY copyKind"%','.join(map(str,inf))))
print("  memcpy on inference streams (kind, per forward, mean us, mean bytes):", [(k,round(c/n,2),round(us,1),int(b)) for k,c,us,b in mc])
