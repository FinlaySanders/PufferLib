#!/usr/bin/env python3
# Independent recomputation of the fixed-model certs from raw records (no shared code with certificates/ledger.py).
# Writes resources/article/RESULTS_INDEPENDENT.md and prints a row-by-row comparison against certificates/results.csv.
import glob, json, csv, hashlib, statistics as st, os
EP="/tmp/reg/article/ep"; GYM="/tmp/reg/article/gym"; CERT="resources/article/certificates"
def stats(v):
    s=sorted(v); n=len(s); q=lambda p: s[int(p*n)]
    return dict(n=n, mean=sum(s)/n, se=st.pstdev(s)/n**.5, median=st.median(s), p10=q(.1), p25=q(.25), p75=q(.75), p90=q(.9))
def ep(f): return [int(l.split()[0]) for l in open(f) if l.strip()][4000:14000]
def gym(d): return [int(json.loads(l)["env_score"]) for f in sorted(glob.glob(f"{d}/w*.jsonl")) for l in open(f) if l.strip()]
runs={}  # id -> (size, interface, scores)
for f in sorted(glob.glob(f"{EP}/fork_fixwt*_s7.ep")):   rid=os.path.basename(f)[:-3]; runs[rid]=(rid[10:12].upper(),"fork",ep(f))
for f in sorted(glob.glob(f"{EP}/stock_fixwt*_s[23][12].ep")): rid=os.path.basename(f)[:-3]; runs[rid]=(rid[11:13].upper(),"stock",ep(f))
for d in sorted(glob.glob(f"{GYM}/r4_fixwt*_4k")):        rid=os.path.basename(d); runs[rid]=(rid[8:10].upper(),"gym",gym(d))
mine={rid:(sz,itf,stats(sc)) for rid,(sz,itf,sc) in runs.items()}
pooled={}
for sz in ("1B","2B","4B"):
    for itf in ("fork","stock","gym"):
        sc=[x for rid,(s,i,v) in runs.items() if s==sz and i==itf for x in v]
        seeds={rid for rid,(s,i,v) in runs.items() if s==sz and i==itf}
        pooled[(sz,itf)]=(stats(sc),sorted(seeds)) if sc and (itf!="gym" or len(seeds)==2) else (None,sorted(seeds))
L=["# Fixed-model results — independent recomputation","",
   "Computed by `independent_results.py` from the raw per-episode records (fork/stock `.ep` logs: completion order, rows 4000:14000 kept; "
   "NetHackChallenge-v0 `r4_*_4k/w*.jsonl`: all 144x28 games, field `env_score`). Median = midpoint for even n; quantiles = sorted[floor(p*n)]; se = population sd / sqrt(n).","",
   "## Pooled per size and interface","","| steps | interface | runs | games | mean | se | median | p25 | p75 | p90 |","|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
for (sz,itf),(p,seeds) in pooled.items():
    if p: L.append(f"| {sz} | {itf} | {len(seeds)} | {p['n']:,} | {p['mean']:,.1f} | {p['se']:,.1f} | {p['median']:,.1f} | {p['p25']:,} | {p['p75']:,} | {p['p90']:,} |")
    else: L.append(f"| {sz} | {itf} | {len(seeds)} | pending (need both seeds at 4,032 games) | | | | | | |")
L+=["","## Per run","","| run | steps | interface | games | mean | se | median | p25 | p75 | p90 |","|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
for rid,(sz,itf,p) in sorted(mine.items(), key=lambda kv:(kv[1][0],kv[1][1],kv[0])):
    L.append(f"| {rid} | {sz} | {itf} | {p['n']:,} | {p['mean']:,.1f} | {p['se']:,.1f} | {p['median']:,.1f} | {p['p25']:,} | {p['p75']:,} | {p['p90']:,} |")
open("resources/article/RESULTS_INDEPENDENT.md","w").write("\n".join(L)+"\n")
print("wrote resources/article/RESULTS_INDEPENDENT.md")
# --- compare with the other agent's results.csv ---
theirs={r["run"]:r for r in csv.DictReader(open(f"{CERT}/results.csv"))}
bad=0; checked=0
for rid,(sz,itf,p) in mine.items():
    t=theirs.get(rid)
    if not t: print("MISSING in theirs:", rid); bad+=1; continue
    checked+=1
    for k,tol in (("n",0.5),("mean",0.05),("se",0.05),("median",0.05),("p10",0.5),("p25",0.5),("p75",0.5),("p90",0.5)):
        if abs(float(t[k])-float(p[k]))>tol: print(f"MISMATCH {rid} {k}: mine {p[k]} theirs {t[k]}"); bad+=1
for rid,t in theirs.items():
    if rid not in mine and rid!="pooled_headline" and "_4k" in rid or (rid not in mine and rid.startswith(("fork_","stock_"))): print("EXTRA in theirs (not recomputed):", rid, t["status"])
print(f"per-run comparison: {checked} runs checked, {bad} discrepancies")
for row in csv.DictReader(open(f"{CERT}/results.csv")):
    if row["run"]=="pooled_headline" and row["n"]:
        p,_=pooled[(row["size"],row["interface"])]
        ok = p and abs(float(row["mean"])-p["mean"])<0.05 and abs(float(row["median"])-p["median"])<0.05 and int(row["n"])==p["n"]
        print(f"pooled {row['size']}/{row['interface']}: theirs {float(row['mean']):.1f}/{float(row['median']):.1f} n={row['n']}  -> {'MATCH' if ok else 'MISMATCH'}")
# --- same raw bytes? ---
def sha(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()
diff=0
for f in glob.glob(f"{EP}/*.ep"):
    b=os.path.basename(f); o=f"{CERT}/raw/{b}"
    if os.path.exists(o) and sha(o)!=sha(f): print("RAW DIFFERS:", b); diff+=1
for f in glob.glob(f"{GYM}/r4_*_4k/w*.jsonl"):
    o=f.replace(GYM, f"{CERT}/raw")
    if os.path.exists(o) and sha(o)!=sha(f): print("RAW DIFFERS:", o); diff+=1
print(f"raw snapshot check: {diff} differing files")
