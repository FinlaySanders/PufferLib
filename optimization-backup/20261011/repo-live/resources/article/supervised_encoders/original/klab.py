# Key-depth lab: do decoder keys need nonlinearity beyond relu(W x)?
# Pointer selection: score = exp(tau) * qhat(ctx) . k(x), CE on correct slot.
# Arms: linear key | r-key (prod, 1 relu) | mid-key (tap after 1 MLP layer) |
# deep-key (dedicated 2-layer). Query path identical and deep everywhere.
# Tasks: A match (easy control) | B wield_best = dmg(id)*(1-cursed)+0.3*ench
#        C quiver_best = rulematch(id,ctx)*quan  (both need per-item products)
import numpy as np, torch, torch.nn as nn
dev = 'cuda'
S, V = 30, 600
rng = np.random.default_rng(5)
DMG = rng.uniform(0, 1, V).astype(np.float32)          # identity->damage LUT
NSK = 3
LT = {k: list(range(10 + 4*k, 14 + 4*k)) for k in range(NSK)}
AT = {k: list(range(30 + 4*k, 34 + 4*k)) for k in range(NSK)}
def gen(N, seed):
    g = np.random.default_rng(seed)
    n = g.integers(4, S, N)
    ids = g.integers(60, V, (N, S))
    occ = np.arange(S)[None, :] < n[:, None]
    cursed = (g.random((N, S)) < .25) & occ
    ench = g.uniform(-1, 1, (N, S)).astype(np.float32) * occ
    quan = g.uniform(0, 1, (N, S)).astype(np.float32) * occ
    sk = g.integers(0, NSK, N)
    ctx = np.zeros((N, 8), np.float32)
    ctx[np.arange(N), sk] = 1
    ctx[:, 3:7] = g.random((N, 4))
    # plant launcher-skill ammo in random slots
    skA = np.full((N, S), -1)
    for i in range(N):
        k = g.integers(1, 4)
        pos = g.choice(n[i], size=min(k, n[i]), replace=False)
        for p in pos:
            s_ = g.integers(0, NSK)
            ids[i, p] = AT[s_][g.integers(4)]
            skA[i, p] = s_
    # targets
    match_ok = (skA == sk[:, None]) & occ
    tA = np.where(match_ok.any(1), np.where(match_ok, g.random((N, S)), -1).argmax(1), -1)
    sB = DMG[ids] * (1 - cursed) + 0.3 * ench
    tB = np.where(occ, sB, -1e9).argmax(1)
    sC = match_ok * quan
    tC = np.where(match_ok.any(1), np.where(match_ok, sC, -1e9).argmax(1), -1)
    sD = ench * (1 - 2 * cursed)              # sign-flip: cursed inverts enchant value
    tD = np.where(occ, sD, -1e9).argmax(1)
    sE = DMG[ids] * quan                      # pure product of two continuous
    tE = np.where(occ, sE, -1e9).argmax(1)
    F = np.stack([occ, cursed, ench, quan], -1).astype(np.float32)
    return (ids, F, occ.astype(np.float32), ctx), {'A_match': tA, 'B_wieldbest': tB,
        'C_quiverbest': tC, 'D_signflip': tD, 'E_product': tE}
Gtr, Ttr = gen(120000, 1); Gva, Tva = gen(24000, 2)
def to_t(G): return tuple(torch.tensor(x, device=dev) for x in G)
Gtr, Gva = to_t(Gtr), to_t(Gva)

class Pointer(nn.Module):
    def __init__(s, arm):
        super().__init__(); s.arm = arm
        s.emb = nn.Embedding(V, 16)
        s.w1 = nn.Linear(20, 16)
        s.m1 = nn.Linear(16, 64)
        s.kproj = nn.Linear(64, 16)
        s.kd = nn.Sequential(nn.Linear(20, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 16))
        s.q = nn.Sequential(nn.Linear(8, 64), nn.ReLU(), nn.Linear(64, 16))
        s.tau = nn.Parameter(torch.tensor(np.log(10.0), dtype=torch.float32))
    def keys(s, x):
        if s.arm == 'linear': return s.w1(x)
        r = torch.relu(s.w1(x))
        if s.arm == 'r': return r
        if s.arm == 'mid': return s.kproj(torch.relu(s.m1(r)))
        return s.kd(x)
    def forward(s, ids, F, occ, ctx):
        x = torch.cat([s.emb(ids), F], -1)
        k = s.keys(x)
        q = s.q(ctx)
        qh = q / (q.norm(dim=-1, keepdim=True) + 1e-6)
        return torch.exp(s.tau) * torch.einsum('bk,bsk->bs', qh, k) - (1 - occ) * 1e9

def run(task):
    ytr = torch.tensor(Ttr[task], device=dev); yva = Tva[task]
    m = np.where(Ttr[task] >= 0)[0]; vm = np.where(yva >= 0)[0]
    print(f'-- {task} (chance ~ {1/17:.2f})')
    for arm in ('linear', 'r', 'mid', 'deep'):
        accs = []
        for sd in (0, 1, 2):
            torch.manual_seed(sd); np.random.seed(sd)
            net = Pointer(arm).to(dev)
            opt = torch.optim.Adam(net.parameters(), lr=1.5e-3)
            for ep in range(12):
                perm = np.random.permutation(m)
                for i in range(0, len(perm), 2048):
                    b = torch.tensor(perm[i:i+2048], device=dev)
                    loss = nn.functional.cross_entropy(net(*[g[b] for g in Gtr]), ytr[b])
                    opt.zero_grad(); loss.backward(); opt.step()
            with torch.no_grad():
                acc = []
                for i in range(0, len(vm), 4096):
                    b = torch.tensor(vm[i:i+4096], device=dev)
                    acc.append((net(*[g[b] for g in Gva]).argmax(-1).cpu().numpy() == yva[b.cpu().numpy()]).mean())
            accs.append(np.mean(acc))
        print(f'   {arm:7s} {np.median(accs):.3f}')
for t in ('D_signflip', 'E_product'): run(t)
