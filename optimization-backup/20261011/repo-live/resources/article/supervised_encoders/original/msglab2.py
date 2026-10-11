# Fine-grained message probe: which species was killed/attacking, from the
# trained msg slice vs fresh text archs.
import numpy as np, torch, torch.nn as nn, re, time
from collections import Counter
dev = 'cuda'; torch.manual_seed(0)
CD = 1046; MSG_LO, MSG_HI = 702, 734
raw = np.fromfile('/tmp/msg_s701.bin', dtype=np.uint8).reshape(-1, CD*4 + 128)
cc = raw[:, :CD*4].copy().view(np.float32).reshape(-1, CD).astype(np.float64)
txt = raw[:, CD*4:]
N = len(raw)
msgs = [bytes(t[t > 0]).decode('latin1').lower() for t in txt]

def build_task(pat, group, min_n=120):
    p = re.compile(pat)
    lab = []
    for m in msgs:
        mt = p.search(m)
        lab.append(mt.group(group).strip() if mt else None)
    cnt = Counter(l for l in lab if l)
    keep = [k for k, v in cnt.most_common(14) if v >= min_n]
    y = np.array([keep.index(l) if l in keep else -1 for l in lab])
    return y, keep
kill_y, kill_c = build_task(r'you kill the (?:poor |invisible )?([a-z][a-z -]+?)[!.]', 1)
atk_y, atk_c = build_task(r'the ([a-z][a-z -]+?) (?:bites|hits|stings|touches|kicks|butts)', 1)
print('kill species:', {k: int((kill_y == i).sum()) for i, k in enumerate(kill_c)}, flush=True)
print('attacker species:', {k: int((atk_y == i).sum()) for i, k in enumerate(atk_c)}, flush=True)

perm = np.random.default_rng(0).permutation(N)
tr, va = perm[:int(N*0.8)], perm[int(N*0.8):]
def multiclass_ridge(X, y, K):
    idx = np.nonzero(y >= 0)[0]
    itr = np.intersect1d(idx, tr); iva = np.intersect1d(idx, va)
    if len(itr) < 300 or len(iva) < 100: return float('nan'), 0
    Xt = torch.tensor(X, dtype=torch.float64, device=dev)
    sd = Xt[torch.tensor(itr, device=dev)].std(0); keep = sd > 1e-4
    Xt = (Xt[:, keep] - Xt[torch.tensor(itr, device=dev)].mean(0)[keep]) / torch.clamp(sd[keep], min=1e-2)
    D = Xt.shape[1]
    Xm = Xt[torch.tensor(itr, device=dev)]
    A = Xm.T @ Xm + 1.0*len(itr)/D * torch.eye(D, dtype=torch.float64, device=dev)
    Ai = torch.linalg.inv(A)
    P = np.zeros((len(iva), K))
    for k in range(K):
        yk = torch.tensor((y == k).astype(float), dtype=torch.float64, device=dev)
        w = Ai @ (Xm.T @ (yk[torch.tensor(itr, device=dev)] - yk[torch.tensor(itr, device=dev)].mean()))
        P[:, k] = (Xt[torch.tensor(iva, device=dev)] @ w).cpu().numpy()
    acc = (P.argmax(1) == y[iva]).mean()
    return acc, len(iva)
ch_t = torch.tensor(txt.astype(np.int64), device=dev)
class CharConv(nn.Module):
    def __init__(s):
        super().__init__(); s.emb = nn.Embedding(256, 16); s.H = 96
        s.c1 = nn.Conv1d(16, 48, 5, padding=2); s.c2 = nn.Conv1d(48, 96, 5, stride=2, padding=2)
    def forward(s, b):
        x = s.emb(ch_t[b]).permute(0, 2, 1)
        return torch.relu(s.c2(torch.relu(s.c1(x)))).max(-1).values
def fresh(y, K, net, epochs=15):
    idx = np.nonzero(y >= 0)[0]
    itr = np.intersect1d(idx, tr); iva = np.intersect1d(idx, va)
    net = net.to(dev); head = nn.Linear(net.H, K).to(dev)
    yt = torch.tensor(y, dtype=torch.long, device=dev)
    opt = torch.optim.Adam(list(net.parameters())+list(head.parameters()), lr=2e-3)
    for ep in range(epochs):
        pm = torch.tensor(np.random.permutation(itr), device=dev)
        for i in range(0, len(pm), 1024):
            b = pm[i:i+1024]
            loss = nn.functional.cross_entropy(head(net(b)), yt[b])
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        vi = torch.tensor(iva, device=dev)
        p = head(net(vi)).argmax(1).cpu().numpy()
    return (p == y[iva]).mean()
for nm, y, cls in [('KILLED species', kill_y, kill_c), ('ATTACKER species', atk_y, atk_c)]:
    K = len(cls)
    base = max((y[va] == k).sum() for k in range(K)) / max((y[va] >= 0).sum(), 1)
    a_msg, n = multiclass_ridge(cc[:, MSG_LO:MSG_HI], y, K)
    a_all, _ = multiclass_ridge(cc, y, K)
    a_cc = fresh(y, K, CharConv())
    print(f'{nm} ({K} classes, val n={n}, majority {base:.2f}): '
          f'RLmsg32 {a_msg:.2f}  RLconcat {a_all:.2f}  charconv-ceiling {a_cc:.2f}', flush=True)
