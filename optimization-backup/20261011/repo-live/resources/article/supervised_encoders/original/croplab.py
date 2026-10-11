# Crop-branch role lab: action-affordance + tactical targets x
# {input encoding, depth, crop size}. Production replica included.
import numpy as np, torch, torch.nn as nn, time
dev = 'cuda'; torch.manual_seed(0)
OBS, ROWS, COLS = 4562, 21, 79
FILES = ['/puffertank/auxdata/farmer.bin', '/puffertank/auxdata/merchant.bin', '/puffertank/auxdata/digger.bin']
CM = 2359
def load(f, PER=50000):
    m = np.memmap(f, dtype=np.uint8, mode='r'); n = min(PER, len(m)//OBS)
    m = m[:n*OBS].reshape(n, OBS)
    gl = m[:, :ROWS*COLS*2].view(np.int16).reshape(n, ROWS, COLS).astype(np.int64)
    bl = m[:, 3318:3318+8].view(np.int32).reshape(n, 2).astype(np.int64)
    return gl, bl
parts = [load(f) for f in FILES]
gl = np.concatenate([p[0] for p in parts]); bl = np.concatenate([p[1] for p in parts])
N = len(gl); hy, hx = bl[:,1], bl[:,0]; ar = np.arange(N)
ci = np.where((gl >= CM) & (gl < CM+96), gl - CM, -1)
WALK = set([12,13,14,19,20,21,22,23,24,25,26,27,28,29,30,31,33,35,36,39,40] + list(range(42,65)))
walk = np.isin(ci, list(WALK)) | (ci == -1)
is_mon = (gl >= 0) & (gl < 1144); is_mon[ar, hy, hx] = False
mp = nn.MaxPool2d(3, 1, 1)
mon_d1 = (mp(torch.tensor(is_mon, device=dev).float().unsqueeze(1)).squeeze(1) > 0).cpu().numpy()
def bfs(src, wk, T=24):
    S = torch.tensor(src, device=dev).float().unsqueeze(1); W = torch.tensor(wk, device=dev).float().unsqueeze(1)
    d = torch.full_like(S, float('inf')); d[S > 0] = 0.0; reach = S
    for t in range(1, T):
        reach = mp(reach) * W
        new = (reach > 0) & torch.isinf(d); d[new] = float(t)
        if not new.any(): break
    return d.squeeze(1).cpu().numpy()
hero = np.zeros((N, ROWS, COLS), bool); hero[ar, hy, hx] = True
d_mon = bfs(is_mon, walk | is_mon | hero)
dm_h = d_mon[ar, hy, hx]
DIRS = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
legal = np.zeros((N, 8)); danger = np.zeros((N, 8)); dmn = np.zeros((N, 8))
for d8, (dy, dx) in enumerate(DIRS):
    yy = np.clip(hy+dy, 0, ROWS-1); xx = np.clip(hx+dx, 0, COLS-1)
    inb = (hy+dy >= 0) & (hy+dy < ROWS) & (hx+dx >= 0) & (hx+dx < COLS)
    legal[:, d8] = walk[ar, yy, xx] & inb & ~is_mon[ar, yy, xx]
    danger[:, d8] = legal[:, d8] * mon_d1[ar, yy, xx]
    dmn[:, d8] = np.where(legal[:, d8] > 0, d_mon[ar, yy, xx], -np.inf)
esc = (dmn > dm_h[:, None]).any(1)
best = dmn.argmax(1)
fs = np.array(DIRS)[best]
nb_walk = legal.sum(1) + np.array([is_mon[ar, np.clip(hy+dy,0,ROWS-1), np.clip(hx+dx,0,COLS-1)].astype(int) for dy,dx in DIRS]).T.sum(1)
pinned = (8 - nb_walk) / 8
choke = nb_walk <= 2
adjm = np.array([is_mon[ar, np.clip(hy+dy,0,ROWS-1), np.clip(hx+dx,0,COLS-1)] for dy, dx in DIRS]).T
flanked = np.zeros(N, bool)
opp = [(0,1),(2,3),(4,7),(5,6)]
for a, b in opp: flanked |= (adjm[:, a] > 0) & (adjm[:, b] > 0)
atk_surface = danger.sum(1)
hm = np.isfinite(dm_h) & (dm_h > 0)
TN = (['leg%d' % i for i in range(8)] + ['dgr%d' % i for i in range(8)]
      + ['esc','fsx_e','fsy_e','pinned','choke','flank','atksurf'])
T = np.concatenate([legal, danger, esc[:,None], fs[:,[1]], fs[:,[0]],
                    pinned[:,None], choke[:,None], flanked[:,None],
                    np.minimum(atk_surface,6)[:,None]/6], 1).astype(np.float32)
M = np.ones((N, 23), np.float32)
for j in range(8, 16): M[:, j] = legal[:, j-8] * (is_mon.any((1,2)))
M[:, 16] = hm; M[:, 17] = M[:, 18] = hm & esc
BIN = set(range(16)) | {16, 20, 21}
val = np.zeros(N, bool); off = 0
for p in parts:
    n = len(p[0]); val[off+int(n*.8):off+n] = True; off += n
tr, va = ar[~val], ar[val]
for k in [17, 18, 19, 22]:
    m = M[tr][:,k] > 0
    if m.sum() > 100:
        mu, sd = T[tr][m,k].mean(), T[tr][m,k].std()+1e-6; T[:,k] = (T[:,k]-mu)/sd
print(f'frames {N} esc-rate {esc[hm].mean():.2f} flank {flanked.mean():.3f}', flush=True)

# class map (semantic input variant): 0 wall/rock 1 floor 2 door 3 hazard-terr 4 monster 5 item 6 stone 7 other
cls = np.full((N, ROWS, COLS), 7, np.int64)
cls[np.isin(ci, list(range(1,12)) + [17,18])] = 0
cls[np.isin(ci, [19,20,21,22])] = 1
cls[np.isin(ci, [12,13,14,15,16])] = 2
cls[np.isin(ci, [32,34,41] + list(range(42,65)))] = 3
cls[is_mon] = 4
cls[((gl >= 1906) & (gl < 2359)) | ((gl >= 1144) & (gl < 1525))] = 5
cls[ci == 0] = 6
GV = 6000; glc = np.clip(gl, 0, GV-1)
g_t = torch.tensor(glc, device=dev); c_t = torch.tensor(cls, device=dev)
hxy = torch.tensor(bl, device=dev)
Yt = torch.tensor(T, device=dev); Mt = torch.tensor(M, device=dev)
def crop(src, b, R, pad):
    B = len(b); H = 2*R+1
    p = torch.full((B, ROWS+2*R, COLS+2*R), pad, dtype=torch.long, device=dev)
    p[:, R:R+ROWS, R:R+COLS] = src[b]
    yy = hxy[b,1][:,None,None] + torch.arange(H, device=dev)[None,:,None]
    xx = hxy[b,0][:,None,None] + torch.arange(H, device=dev)[None,None,:]
    return p[torch.arange(B, device=dev)[:,None,None], yy, xx]
class Arch(nn.Module):
    def __init__(s, inp, R, depth, H=256):
        super().__init__(); s.inp = inp; s.R = R; s.H = H
        ed = 32 if inp == 'glyph' else 8
        s.emb = nn.Embedding(GV if inp == 'glyph' else 9, ed)
        D = (2*R+1)**2 * ed
        if depth == 1: s.net = nn.Sequential(nn.Linear(D, H), nn.ReLU())
        else: s.net = nn.Sequential(nn.Linear(D, 384), nn.ReLU(), nn.Linear(384, H), nn.ReLU())
    def forward(s, b):
        src, pad = (g_t, GV-1) if s.inp == 'glyph' else (c_t, 8)
        return s.net(s.emb(crop(src, b, s.R, pad)).reshape(len(b), -1))
def auc(y, p):
    o = np.argsort(p); rk = np.empty(len(p)); rk[o] = np.arange(1, len(p)+1)
    pos = y > 0.5; npos, nneg = pos.sum(), (~pos).sum()
    if npos < 30 or nneg < 30: return float('nan')
    return (rk[pos].sum() - npos*(npos+1)/2) / (npos*nneg)
def run(name, net, epochs=20, BS=2048):
    net = net.to(dev); head = nn.Linear(net.H, 23).to(dev)
    opt = torch.optim.Adam(list(net.parameters())+list(head.parameters()), lr=1.5e-3)
    t0 = time.time()
    for ep in range(epochs):
        pm = torch.tensor(np.random.permutation(tr), device=dev)
        for i in range(0, len(pm), BS):
            b = pm[i:i+BS]
            p = head(net(b))
            loss = (nn.functional.smooth_l1_loss(p, Yt[b], reduction='none')*Mt[b]).sum()/Mt[b].sum()
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        vi = torch.tensor(va, device=dev)
        p = torch.cat([head(net(vi[i:i+BS])) for i in range(0, len(vi), BS)]).cpu().numpy()
    leg = np.mean([auc(T[va,k], p[:,k]) for k in range(8)])
    dgr = np.nanmean([auc(T[va,k], p[:,k]) if M[va][:,k].sum()>200 else np.nan for k in range(8,16)])
    rest = []
    for k in range(16, 23):
        mv = M[va][:,k] > 0
        if mv.sum() < 300: rest.append(float('nan')); continue
        yv, pv = T[va][mv,k], p[mv,k]
        rest.append(auc(yv, pv) if k in BIN else 1-((yv-pv)**2).sum()/max(((yv-yv.mean())**2).sum(),1e-9))
    print(f'{name:14s} legal {leg:.3f}  danger {dgr:.3f}  ' +
          ''.join(f'{TN[16+i]} {r:.2f}  ' if r==r else f'{TN[16+i]} -  ' for i, r in enumerate(rest)) +
          f'{time.time()-t0:.0f}s', flush=True)
run('prod(g,9,1L)', Arch('glyph', 4, 1))
run('glyph,9,2L', Arch('glyph', 4, 2))
run('class,9,1L', Arch('class', 4, 1))
run('class,9,2L', Arch('class', 4, 2))
run('class,5,2L', Arch('class', 2, 2))
run('class,13,2L', Arch('class', 6, 2))
