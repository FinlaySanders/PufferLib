import numpy as np, torch, torch.nn as nn
torch.manual_seed(0)
dev = 'cuda'
z = np.load('/tmp/spell_feats.npz')
keys = torch.tensor(z['keys'].reshape(-1, 8, 16), dtype=torch.float32)
nsp, ids, lev, fail, know = z['nsp'], z['ids'], z['lev'], z['fail'], z['know']
N = len(nsp)
occ = torch.tensor((ids > 0).astype(np.float32))          # (N,8)
has = nsp > 0
from collections import Counter
c = Counter(ids[has].ravel()); c.pop(0, None)
top = [k for k, _ in c.most_common(5)]
# targets: [n_spells(reg), 5x has_book(bin), min_fail(reg), max_level(reg), forget(bin)]
minfail = np.where(has, np.min(np.where(ids > 0, fail, 999), 1), 0) / 100.0
maxlev = np.where(has, np.max(np.where(ids > 0, lev, 0), 1), 0) / 7.0
forget = np.where(has, (np.where(ids > 0, know, 99999) < 2000).any(1), 0)
Y = np.stack([np.minimum(nsp, 4) / 4.0] + [(ids == k).any(1) for k in top]
             + [np.clip(minfail, 0, 1), maxlev, forget], 1).astype(np.float32)
M = np.stack([np.ones(N)] + [has]*5 + [has]*3, 1).astype(np.float32)  # loss masks
ISBIN = [0,1,1,1,1,1,0,0,1]
NAMES = ["n_spells","bk348","bk365","bk379","bk350","bk377","min_fail","max_lev","forget"]
Y, Mk = torch.tensor(Y), torch.tensor(M)
rng = np.random.default_rng(0); perm = rng.permutation(N)
tr, va = torch.tensor(perm[:int(N*.8)]), torch.tensor(perm[int(N*.8):])

# raw slot inputs for the from-scratch control
w = np.load('/tmp/spellw.npy', allow_pickle=True).item()
import re
txt = open('/puffertank/pufferlib/ocean/nethack/glyph_map.h').read()
def arr(name):
    m = re.search(name + r"\[\d+\] = \{([0-9,\-]+)\};", txt)
    return np.array([int(x) for x in m.group(1).split(",") if x], dtype=np.int64)
E = (w['E'] + w['K'][arr("nh_glyph_kind")] + w['S'][arr("nh_glyph_sub")]).astype(np.float32)
sg = np.clip(ids + 1906, None, 5975)
emb = np.where((ids > 0)[..., None], E[sg], 0.0).astype(np.float32)
sc = np.stack([(ids > 0).astype(np.float32), np.clip(lev*0.142857, None, 1.0),
               np.clip(fail*0.01, None, 1.0), np.clip(know*0.00005, None, 1.0)], -1).astype(np.float32)
Xraw = torch.tensor(np.concatenate([emb, sc], -1))          # (N,8,36)

class Arm(nn.Module):
    def __init__(self, kind, width=16):
        super().__init__()
        self.kind, self.w = kind, width
        K = 16
        if kind == "max":    self.W = nn.Linear(K, width)
        if kind == "isum":   self.W = nn.Linear(K, width)
        if kind == "summax": self.W = nn.Linear(K, width // 2)
        if kind == "attn":   self.Q = nn.Parameter(torch.randn(width // K if width >= K else 1, K) * .3); self.w = (width // K) * K
        if kind == "scratch":
            self.W1 = nn.Linear(36, 16); self.W = nn.Linear(16, width)
        d = {"sum": 16, "mean": 16}.get(kind, self.w)
        self.head = nn.Linear(d, 9)
    def forward(self, k, occm, xraw=None):
        if self.kind == "scratch":
            k = torch.relu(self.W1(xraw))
        if self.kind == "sum":    s = k.sum(1)
        elif self.kind == "mean": s = k.sum(1) / occm.sum(1, keepdim=True).clamp(min=1)
        elif self.kind == "max":  s = torch.relu(self.W(k).max(1).values)
        elif self.kind in ("isum", "scratch"): s = (torch.relu(self.W(k)) * occm[..., None]).sum(1) * 0.2
        elif self.kind == "summax":
            a = (torch.relu(self.W(k)) * occm[..., None]).sum(1) * 0.2
            s = torch.cat([a, torch.relu(self.W(k)).max(1).values], 1)
        elif self.kind == "attn":
            att = torch.softmax(torch.einsum('mk,nsk->nsm', self.Q, k), 1)
            s = torch.einsum('nsm,nsk->nmk', att, k).reshape(len(k), -1)
        return self.head(s)

def run(kind, width=16, epochs=6):
    m = Arm(kind, width).to(dev)
    opt = torch.optim.Adam(m.parameters(), lr=3e-3)
    Kd, Od, Yd, Md, Xd = keys.to(dev), occ.to(dev), Y.to(dev), Mk.to(dev), Xraw.to(dev)
    for ep in range(epochs):
        for i in range(0, len(tr), 8192):
            b = tr[i:i+8192].to(dev)
            p = m(Kd[b], Od[b], Xd[b])
            loss = 0
            for j in range(9):
                t, msk = Yd[b, j], Md[b, j]
                l = (nn.functional.binary_cross_entropy_with_logits(p[:, j], t, reduction='none')
                     if ISBIN[j] else (p[:, j] - t) ** 2)
                loss = loss + (l * msk).sum() / msk.sum().clamp(min=1)
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        b = va.to(dev)
        p = m(Kd[b], Od[b], Xd[b]).cpu().numpy()
    res = []
    for j in range(9):
        msk = M[va.numpy(), j] > 0
        yv, pv = Y[va][msk, j].numpy(), p[msk, j]
        if ISBIN[j]:
            pos, neg = pv[yv == 1], pv[yv == 0]
            res.append((pos[:, None] > neg[None, :]).mean() if len(pos) and len(neg) else float('nan'))
        else:
            res.append(1 - ((yv - pv) ** 2).mean() / yv.var())
    return res

ARMS = [("max16 (current)", "max", 16), ("sum16 (free)", "sum", 16), ("mean16", "mean", 16),
        ("isum16", "isum", 16), ("isum32", "isum", 32), ("summax32", "summax", 32),
        ("attn2x16", "attn", 32), ("scratch-isum16", "scratch", 16)]
print(f"{'arm':<16}" + "".join(f"{n:>9}" for n in NAMES))
for label, kind, width in ARMS:
    r = run(kind, width)
    print(f"{label:<16}" + "".join(f"{v:>9.3f}" for v in r))
