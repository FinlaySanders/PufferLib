import re, glob, os, sys
SP = "/puffertank/pufferlib"
def load(d):
    out = {}
    for f in sorted(glob.glob(d + "/w*.err")):
        w = os.path.basename(f).split('.')[0]
        eps = []
        for l in open(f, errors="replace"):
            if "episode end" in l:
                m = dict(re.findall(r'(\w+)=([-\d.]+)', l))
                eps.append((float(m.get('score', 0)), float(m.get('game_t', 0)), int(float(m.get('role', -1)))))
        out[w] = eps
    return out
A, B = sys.argv[1], sys.argv[2]
F, S = load(SP + "/cert/" + A), load(SP + "/cert/" + B)
tf, ts = [], []
print(f"{'worker':7s} {'n':>3s}  {A+'_med':>10s} {B+'_med':>11s}   first pairs")
for w in sorted(set(F) & set(S)):
    n = min(len(F[w]), len(S[w]))
    if not n: continue
    f = [F[w][i][0] for i in range(n)]; s = [S[w][i][0] for i in range(n)]
    tf += f; ts += s
    print(f"{w:7s} {n:3d}  {sorted(f)[len(f)//2]:10.0f} {sorted(s)[len(s)//2]:11.0f}   "
          + " ".join(f"{int(a)}/{int(b)}" for a, b in list(zip(f, s))[:6]))
if tf:
    print(f"\nPAIRED n={len(tf)}  {A} median={sorted(tf)[len(tf)//2]:.0f}  {B} median={sorted(ts)[len(ts)//2]:.0f}")
    print(f"identical: {sum(1 for a,b in zip(tf,ts) if a==b)}/{len(tf)}   "
          f"{A} higher: {sum(1 for a,b in zip(tf,ts) if a>b)}   {B} higher: {sum(1 for a,b in zip(tf,ts) if b>a)}")
