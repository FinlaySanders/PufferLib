# Branch lab v4: the quality x speed frontier for the global branch.
# Entity-sparse tokenization (K nearest monsters+items + stairs token),
# dense baselines, standardized targets, per-row timing.
import json, sys, time, numpy as np, torch, torch.nn as nn
dev = 'cuda'; torch.manual_seed(0)
L = json.load(open('/tmp/aux_layout.json'))
OBS, OE, AUX, ROWS, COLS = L['obs_size'], L['off_extra'], L['aux_idx'], L['rows'], L['cols']
FILES = ['/puffertank/auxdata/farmer.bin','/puffertank/auxdata/merchant.bin','/puffertank/auxdata/digger.bin']

def load(f, n=65000):
    m = np.memmap(f, dtype=np.uint8, mode='r'); n = min(n, len(m)//OBS)
    m = m[:n*OBS].reshape(n, OBS)
    gl = m[:, :ROWS*COLS*2].view(np.int16).reshape(n, ROWS, COLS).astype(np.int64)
    bl = m[:, L['off_blstats']:L['off_blstats']+8].view(np.int32).reshape(n, 2).astype(np.int64)
    ax = m[:, OE+4*AUX:OE+4*(AUX+10)].view(np.int32).reshape(n, 10).astype(np.float32)
    return gl, bl, ax
parts = [load(f) for f in FILES]
gl = np.concatenate([p[0] for p in parts]); bl = np.concatenate([p[1] for p in parts])
ax = np.concatenate([p[2] for p in parts]); N = len(gl)
print(f'frames {N}', flush=True)
ISM = ((gl>=0)&(gl<381)) | ((gl>=762)&(gl<1144))
ISI = (gl>=1906)&(gl<2360)

# ---- targets (20, standardized) ----
KMAX = 64
T = np.zeros((N, 20), np.float32); M = np.ones((N, 20), np.float32)
ent_g = np.zeros((N, KMAX), np.int64); ent_f = np.zeros((N, KMAX, 4), np.float32)
for i in range(N):
    hx, hy = bl[i,0], bl[i,1]
    rr, cc = np.nonzero(ISM[i] | ISI[i])
    keep = ~((cc==hx)&(rr==hy)); rr, cc = rr[keep], cc[keep]
    dx, dy = cc-hx, rr-hy; d = np.maximum(np.abs(dx),np.abs(dy))
    o = np.argsort(d)[:KMAX]
    k = len(o)
    ent_g[i,:k] = gl[i, rr[o], cc[o]]
    ent_f[i,:k,0] = dy[o]/10.; ent_f[i,:k,1] = dx[o]/20.
    ent_f[i,:k,2] = np.minimum(d[o],15)/15.; ent_f[i,:k,3] = 1.0
    mon = ISM[i, rr, cc]
    om = np.argsort(np.where(mon, d, 999))
    nmon = mon.sum()
    if nmon >= 1: j = om[0]; T[i,2:5] = (dx[j]/20, dy[j]/10, min(d[j],15)/15)
    else: M[i,2:5] = 0
    if nmon >= 2: j = om[1]; T[i,5:8] = (dx[j]/20, dy[j]/10, min(d[j],15)/15)
    else: M[i,5:8] = 0
    T[i,8] = min(nmon,16)/16
    for kq,(qx,qy) in enumerate([(-1,-1),(1,-1),(-1,1),(1,1)]):
        T[i,9+kq] = min(((np.sign(dx)==qx)&(np.sign(dy)==qy)&mon).sum(),8)/8
    it = ~mon
    oi = np.argsort(np.where(it, d, 999))
    nit = it.sum()
    if nit >= 1: j = oi[0]; T[i,13:16] = (dx[j]/20, dy[j]/10, min(d[j],15)/15)
    else: M[i,13:16] = 0
    T[i,16] = min(nit,16)/16
T[:,0] = ax[:,1]/40; T[:,1] = ax[:,2]/10; M[:,0] = M[:,1] = ax[:,0]
T[:,17] = ax[:,4]/20; T[:,18] = ax[:,5]/10; M[:,17] = M[:,18] = (ax[:,3]<15)
T[:,19] = np.minimum(ax[:,6],16)/16
# standardize each target on masked train rows
val_mask = np.zeros(N, bool); off = 0
for p in parts:
    n = len(p[0]); val_mask[off+int(n*.8):off+n] = True; off += n
tr, va = np.arange(N)[~val_mask], np.arange(N)[val_mask]
for k in range(20):
    m = (M[tr][:,k] > 0)
    mu, sd = T[tr][m,k].mean(), T[tr][m,k].std() + 1e-6
    T[:,k] = (T[:,k] - mu) / sd
NAMES = ['ds_dx','ds_dy','nm1_dx','nm1_dy','nm1_d','nm2_dx','nm2_dy','nm2_d','mcnt',
         'qNW','qNE','qSW','qSE','ni_dx','ni_dy','ni_d','icnt','nh_dx','nh_dy','nhcnt']
CORE = [0,2,3,4,5,8]
GV = 6000
gl = np.clip(gl,0,GV-1); ent_g = np.clip(ent_g,0,GV-1)
# stairs synthetic token appended per frame (from aux): glyph id GV-1 reserved
ds_tok_f = np.stack([ax[:,2]/10., ax[:,1]/40., np.maximum(np.abs(ax[:,1]),np.abs(ax[:,2]))/15., ax[:,0]], 1).astype(np.float32)

class Dense(nn.Module):
    def __init__(s, H=128, heads=8, deep=False):
        super().__init__(); s.emb = nn.Embedding(GV,29); s.h = heads; s.H = H
        s.v = nn.Sequential(nn.Linear(32,H), nn.ReLU(), nn.Linear(H,H)) if deep else nn.Linear(32,H)
        s.a = nn.Linear(32,heads)
    def forward(s, g, hxy, eg, ef, dst):
        B, R, C = g.shape
        yy, xx = torch.meshgrid(torch.arange(R,device=dev), torch.arange(C,device=dev), indexing='ij')
        dy = yy.unsqueeze(0)-hxy[:,1].view(-1,1,1); dx = xx.unsqueeze(0)-hxy[:,0].view(-1,1,1)
        rel = torch.stack([dy/10., dx/20., torch.maximum(dx.abs(),dy.abs())/15.], -1)
        t = torch.cat([s.emb(g), rel], -1).flatten(1,2)
        v = torch.relu(s.v(t)).view(B,-1,s.h,s.H//s.h)
        a = torch.softmax(s.a(t),1)
        return (v*a.unsqueeze(-1)).sum(1).flatten(1)

class Sparse(nn.Module):
    def __init__(s, K=32, H=128, heads=8, deep=False, pool='attn'):
        super().__init__(); s.K = K; s.h = heads; s.H = H; s.pool = pool
        s.emb = nn.Embedding(GV,28)
        vin = 32
        s.v = nn.Sequential(nn.Linear(vin,H), nn.ReLU(), nn.Linear(H,H)) if deep else nn.Linear(vin,H)
        s.a = nn.Linear(vin,heads)
        s.ds = nn.Linear(4, vin)  # stairs synthetic token
    def forward(s, g, hxy, eg, ef, dst):
        B = eg.shape[0]
        t = torch.cat([s.emb(eg[:,:s.K]), ef[:,:s.K]], -1)
        dstok = s.ds(dst).unsqueeze(1)
        t = torch.cat([t, dstok], 1)
        alive = torch.cat([ef[:,:s.K,3], torch.ones(B,1,device=dev)], 1)
        v = torch.relu(s.v(t))
        if s.pool == 'max':
            v = v.masked_fill(alive.unsqueeze(-1) < .5, -1e9)
            return v.max(1).values
        v = v.view(B,-1,s.h,s.H//s.h)
        logits = s.a(t).masked_fill(alive.unsqueeze(-1) < .5, -1e9)
        a = torch.softmax(logits,1)
        return (v*a.unsqueeze(-1)).sum(1).flatten(1)

def run(name, net, epochs=24, dump=False):
    net = net.to(dev); H = net.H if hasattr(net,'H') else 128
    head = nn.Linear(H, 20).to(dev)
    opt = torch.optim.Adam(list(net.parameters())+list(head.parameters()), lr=1.5e-3)
    g_t = torch.from_numpy(gl).to(dev); hxy = torch.from_numpy(bl).to(dev)
    eg = torch.from_numpy(ent_g).to(dev); ef = torch.from_numpy(ent_f).to(dev)
    dst = torch.from_numpy(ds_tok_f).to(dev)
    Yt = torch.from_numpy(T).to(dev); Mt = torch.from_numpy(M).to(dev)
    BS = 2048
    t0 = time.time()
    for ep in range(epochs):
        perm = torch.from_numpy(np.random.permutation(tr)).to(dev)
        for i in range(0, len(perm), BS):
            b = perm[i:i+BS]
            p = head(net(g_t[b], hxy[b], eg[b], ef[b], dst[b])); mb = Mt[b]
            loss = (torch.nn.functional.smooth_l1_loss(p, Yt[b], reduction='none')*mb).sum()/mb.sum()
            opt.zero_grad(); loss.backward(); opt.step()
    ttrain = time.time() - t0
    with torch.no_grad():
        torch.cuda.synchronize(); t0 = time.time()
        for i in range(0, 65536, BS):
            net(g_t[i:i+BS], hxy[i:i+BS], eg[i:i+BS], ef[i:i+BS], dst[i:i+BS])
        torch.cuda.synchronize(); tinf = 65536/(time.time()-t0)
        vi = torch.from_numpy(va).to(dev)
        p = torch.cat([head(net(g_t[vi[i:i+BS]], hxy[vi[i:i+BS]], eg[vi[i:i+BS]], ef[vi[i:i+BS]], dst[vi[i:i+BS]])) for i in range(0,len(vi),BS)]).cpu().numpy()
    r2s = {}
    for k in range(20):
        mv = M[va][:,k] > 0
        if mv.sum() < 100: continue
        yv, pv = T[va][mv,k], p[mv,k]
        r2s[k] = 1 - ((yv-pv)**2).sum()/max(((yv-yv.mean())**2).sum(),1e-9)
    if dump:
        for k in sorted(r2s): print(f'   {NAMES[k]:8s} {r2s[k]:10.2f}', flush=True)
    core = [f'{r2s.get(c,float("nan")):.2f}' for c in CORE]
    print(('{:14s}'+'{:>7s}'*6+'{:>7s}{:>9s}{:>9s}').format(name, *core,
        f'{np.mean(list(r2s.values())):.2f}', f'{ttrain:.0f}s', f'{tinf/1e6:.2f}Mf/s'), flush=True)

print(('{:14s}'+'{:>7s}'*6+'{:>7s}{:>9s}{:>9s}').format('arch','ds_dx','nm1dx','nm1dy','nm1d','nm2dx','mcnt','mean','train','infer'), flush=True)
run('sp32deep', Sparse(32,128,8,deep=True), 96, dump=True)
run('sp64deep', Sparse(64,128,8,deep=True), 96)
run('sp64wide', Sparse(64,256,16,deep=True), 96)
run('sp32max', Sparse(32,128,8,pool='max'), 96)

