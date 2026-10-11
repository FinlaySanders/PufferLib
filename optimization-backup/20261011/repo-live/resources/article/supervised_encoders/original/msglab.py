# Message-branch lab: (a) do event classes decode from the TRAINED policy's
# 32-dim msg slice? (b) supervised ceiling: trigram-bag replica vs
# alternatives (bigger vocab, char-conv, word-bag) on the same labels.
import numpy as np, torch, torch.nn as nn, re, time
dev = 'cuda'; torch.manual_seed(0)
CD = 1046; MSG_LO, MSG_HI = 702, 734
raw = np.fromfile('/tmp/msg_s701.bin', dtype=np.uint8).reshape(-1, CD*4 + 128)
cc = raw[:, :CD*4].copy().view(np.float32).reshape(-1, CD).astype(np.float64)
txt = raw[:, CD*4:]
N = len(raw)
msgs = [bytes(t[t > 0]).decode('latin1').lower() for t in txt]
nonempty = np.array([len(m) > 0 for m in msgs])
print(f'frames {N}, nonempty toplines {nonempty.sum()} ({100*nonempty.mean():.0f}%)', flush=True)

# event taxonomy (engine-truth = the text itself; regex labels)
CLASSES = [
    ('you_kill',   r'you (kill|destroy)'),
    ('you_hit',    r'you (hit|smite|bash|kick.*!)|your .* hits'),
    ('enemy_hits', r'(hits!|hits you|bites!|bites you|touches you|stings)'),
    ('enemy_miss', r'(misses|just misses|swings wildly)'),
    ('item_found', r'you (see here|find|pick up)|^[a-z] - '),
    ('hunger',     r'(hungry|weak from|fainting|starving)'),
    ('feel_msg',   r'you feel'),
    ('door',       r'(door|the stairs|staircase|broken)'),
    ('shop',       r'(costs|zorkmid|for sale|welcome to|pay)'),
    ('pray_god',   r'(pray|voice|feels? (that )?you|pleased)'),
    ('welcome_lvl',r'(welcome to experience|feel more confident)'),
    ('danger_stat',r'(poison|sick|confus|stun|blind|paraly)'),
]
Y = np.zeros((N, len(CLASSES)))
for j, (nm, pat) in enumerate(CLASSES):
    p = re.compile(pat)
    Y[:, j] = [1.0 if p.search(m) else 0.0 for m in msgs]
for j, (nm, _) in enumerate(CLASSES):
    print(f'  {nm:12s} {int(Y[:,j].sum()):6d} frames', flush=True)

perm = np.random.default_rng(0).permutation(N)
tr, va = perm[:int(N*0.8)], perm[int(N*0.8):]
def auc(y, p):
    o = np.argsort(p); rk = np.empty(len(p)); rk[o] = np.arange(1, len(p)+1)
    pos = y > 0.5; npos, nneg = pos.sum(), (~pos).sum()
    if npos < 30 or nneg < 30: return float('nan')
    return (rk[pos].sum() - npos*(npos+1)/2) / (npos*nneg)

# (a) ridge decode from the trained msg slice + full concat
def ridge_dec(X):
    Xt = torch.tensor(X, dtype=torch.float64, device=dev)
    sd = Xt[torch.tensor(tr, device=dev)].std(0); keep = sd > 1e-4
    Xt = (Xt[:, keep] - Xt[torch.tensor(tr, device=dev)].mean(0)[keep]) / torch.clamp(sd[keep], min=1e-2)
    D = Xt.shape[1]
    out = []
    Xm = Xt[torch.tensor(tr, device=dev)]
    A = Xm.T @ Xm + 1.0*len(tr)/D * torch.eye(D, dtype=torch.float64, device=dev)
    Ai = torch.linalg.inv(A)
    for j in range(len(CLASSES)):
        y = torch.tensor(Y[:, j], dtype=torch.float64, device=dev)
        w = Ai @ (Xm.T @ (y[torch.tensor(tr, device=dev)] - y[torch.tensor(tr, device=dev)].mean()))
        p = (Xt[torch.tensor(va, device=dev)] @ w).cpu().numpy()
        out.append(auc(Y[va, j], p))
    return out
r_msg = ridge_dec(cc[:, MSG_LO:MSG_HI])
r_all = ridge_dec(cc)

# (b) supervised ceiling: fresh architectures on the raw text
def trigram_ids(vocab_bits):
    V = 1 << vocab_bits
    ids = np.full((N, 126), -1, np.int64)
    for i, t in enumerate(txt):
        m = t.copy()
        m[(m >= 65) & (m <= 90)] += 32
        L = int((m > 0).argmin()) if (m > 0).any() and not (m > 0).all() else (128 if (m > 0).all() else 0)
        for k in range(max(L - 2, 0)):
            key = (int(m[k]) << 16) | (int(m[k+1]) << 8) | int(m[k+2])
            ids[i, k] = ((key * 2654435761) & 0xFFFFFFFF) >> (32 - vocab_bits)
    return ids
tri12 = trigram_ids(12)
ch_t = torch.tensor(txt.astype(np.int64), device=dev)
Yt = torch.tensor(Y, dtype=torch.float32, device=dev)
class TriBag(nn.Module):  # production replica (sum bag, /sqrt(n+1))
    def __init__(s, V=4096, D=32):
        super().__init__(); s.emb = nn.Embedding(V+1, D, padding_idx=V); s.V = V; s.H = D
        s.ids = torch.tensor(np.where(tri12 >= 0, tri12, V), device=dev)
    def forward(s, b):
        e = s.emb(s.ids[b])
        n = (s.ids[b] != s.V).sum(1, keepdim=True).float()
        return e.sum(1) / torch.sqrt(n + 1)
class TriBagBig(TriBag):
    def __init__(s): super().__init__(); s.emb = nn.Embedding(4097, 64, padding_idx=4096); s.H = 64
class CharConv(nn.Module):
    def __init__(s):
        super().__init__(); s.emb = nn.Embedding(256, 16); s.H = 96
        s.c1 = nn.Conv1d(16, 48, 5, padding=2); s.c2 = nn.Conv1d(48, 96, 5, stride=2, padding=2)
    def forward(s, b):
        x = s.emb(ch_t[b]).permute(0, 2, 1)
        x = torch.relu(s.c1(x)); x = torch.relu(s.c2(x))
        return x.max(-1).values
def run(name, net, epochs=8, BS=2048):
    net = net.to(dev); head = nn.Linear(net.H, len(CLASSES)).to(dev)
    opt = torch.optim.Adam(list(net.parameters())+list(head.parameters()), lr=2e-3)
    t0 = time.time()
    for ep in range(epochs):
        pm = torch.tensor(np.random.permutation(tr), device=dev)
        for i in range(0, len(pm), BS):
            b = pm[i:i+BS]
            loss = nn.functional.binary_cross_entropy_with_logits(head(net(b)), Yt[b])
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        vi = torch.tensor(va, device=dev)
        p = torch.cat([head(net(vi[i:i+BS])) for i in range(0, len(vi), BS)]).cpu().numpy()
    return [auc(Y[va, j], p[:, j]) for j in range(len(CLASSES))], time.time()-t0

rows = [('RLmsg32(ridge)', r_msg, 0.0), ('RLconcat(ridge)', r_all, 0.0)]
for nm, net in [('tribag32', TriBag()), ('tribag64', TriBagBig()), ('charconv', CharConv())]:
    res, dt = run(nm, net)
    rows.append((nm, res, dt))
print('\n' + f'{"arch":16s}' + ''.join(f'{nm:>11s}' for nm, _ in CLASSES))
for nm, res, dt in rows:
    print(f'{nm:16s}' + ''.join(f'{v:11.2f}' if v == v else f'{"-":>11s}' for v in res) + (f'  {dt:.0f}s' if dt else ''))
