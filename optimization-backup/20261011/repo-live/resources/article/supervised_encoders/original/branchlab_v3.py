# Branch lab v3: best-form search per encoder branch.
# Tracks: GEO (global spatial), LOCAL (ego crop tactical), INV (slot
# conjunctions). AUC for binary targets, R2 for continuous; val/train.
import json, sys, numpy as np, torch, torch.nn as nn
dev = 'cuda'
torch.manual_seed(0)

L = json.load(open('/tmp/aux_layout.json'))
OBS, OE, AUX, ROWS, COLS = L['obs_size'], L['off_extra'], L['aux_idx'], L['rows'], L['cols']
FILES = ['/puffertank/auxdata/farmer.bin', '/puffertank/auxdata/merchant.bin', '/puffertank/auxdata/digger.bin']
PER = int(sys.argv[1]) if len(sys.argv) > 1 else 65000
EP_GEO, EP_LOC, EP_INV = 36, 24, 24

def load(f, n):
    m = np.memmap(f, dtype=np.uint8, mode='r')
    n = min(n, len(m) // OBS)
    m = m[:n * OBS].reshape(n, OBS)
    gl = m[:, :ROWS * COLS * 2].view(np.int16).reshape(n, ROWS, COLS).astype(np.int64)
    bl = m[:, L['off_blstats']:L['off_blstats'] + 8].view(np.int32).reshape(n, 2).astype(np.int64)
    ax = m[:, OE + 4 * AUX:OE + 4 * (AUX + 10)].view(np.int32).reshape(n, 10).astype(np.float32)
    inv = m[:, L['off_inv']:L['off_inv'] + 110].view(np.int16).reshape(n, 55).astype(np.int64)
    ist = m[:, L['off_invst']:L['off_invst'] + 440].reshape(n, 55, 8).astype(np.int64)
    return gl, bl, ax, inv, ist

parts = [load(f, PER) for f in FILES]
gl, bl, ax, inv, ist = [np.concatenate([p[i] for p in parts]) for i in range(5)]
N = len(gl)
print(f'frames {N}', flush=True)
ISM = ((gl >= 0) & (gl < 381)) | ((gl >= 762) & (gl < 1144))

def mon_targets(gl, bl):
    out = np.zeros((len(gl), 3), np.float32)
    for i in range(len(gl)):
        rr, cc = np.nonzero(ISM[i])
        hx, hy = bl[i, 0], bl[i, 1]
        keep = ~((cc == hx) & (rr == hy))
        rr, cc = rr[keep], cc[keep]
        if len(rr) == 0: out[i] = (0, 0, 15); continue
        dx, dy = cc - hx, rr - hy
        d = np.maximum(np.abs(dx), np.abs(dy))
        j = d.argmin()
        out[i] = (dx[j], dy[j], min(d[j], 15))
    return out
MT = mon_targets(gl, bl)
ones = np.ones(N, np.float32)

GEO_Y = np.stack([ax[:,1]/40, ax[:,2]/10, MT[:,0]/20, MT[:,1]/10, MT[:,2]/15,
                  np.minimum(ax[:,6],16)/16], 1).astype(np.float32)
GEO_M = np.stack([ax[:,0], ax[:,0], (MT[:,2]<15), (MT[:,2]<15), ones, ones], 1).astype(np.float32)
GEO_NAMES = ['ds_dx','ds_dy','nm_dx','nm_dy','nm_dist','nh_cnt']
GEO_BIN = [False]*6

# LOCAL: 11x11 ego crop; targets: adjacent-monster bits (8-way) + nearest
# in-crop monster dx/dy (cheb<=5)
PAD = 5
glp = np.pad(gl, ((0,0),(PAD,PAD),(PAD,PAD)))
rows_i = (bl[:,1,None] + np.arange(11)[None,:])
cols_i = (bl[:,0,None] + np.arange(11)[None,:])
CROP = glp[np.arange(N)[:,None,None], rows_i[:,:,None], cols_i[:,None,:]]
ismc = ((CROP >= 0) & (CROP < 381)) | ((CROP >= 762) & (CROP < 1144))
D8 = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
ADJ = np.stack([ismc[:, 5+dy, 5+dx] for dy,dx in D8], 1).astype(np.float32)
def crop_nm(ismc):
    out = np.zeros((N,3), np.float32)
    ismc2 = ismc.copy(); ismc2[:,5,5] = False
    for i in range(N):
        rr, cc = np.nonzero(ismc2[i])
        if len(rr) == 0: out[i] = (0,0,6); continue
        dy, dx = rr-5, cc-5
        d = np.maximum(np.abs(dx), np.abs(dy))
        j = d.argmin()
        out[i] = (dx[j], dy[j], d[j])
    return out
CM = crop_nm(ismc)
LOC_Y = np.concatenate([ADJ, np.stack([CM[:,0]/5, CM[:,1]/5, CM[:,2]/6], 1)], 1).astype(np.float32)
LOC_M = np.concatenate([np.ones((N,8),np.float32), np.stack([(CM[:,2]<6)]*2+[ones],1)], 1).astype(np.float32)
LOC_NAMES = ['aNW','aN','aNE','aW','aE','aSW','aS','aSE','cnm_dx','cnm_dy','cnm_d']
LOC_BIN = [True]*8 + [False]*3

OBJ_OFF = 1906
ot = np.where(inv > 0, inv - OBJ_OFF, -1)
is_l = (ot >= 65) & (ot <= 70); is_am = ((ot >= 1) & (ot <= 6)) | (ot == 445) | (ot == 446)
bow = (ot >= 66) & (ot <= 69); arrow = (ot >= 1) & (ot <= 4)
xbow = ot == 70; bolt = (ot >= 5) & (ot <= 6)
wld = (ist[:,:,5] & 2) > 0
INV_Y = np.stack([(inv>0).sum(1)/55.0, is_l.any(1), is_am.any(1),
                  ((bow.any(1)&arrow.any(1))|(xbow.any(1)&bolt.any(1))),
                  (wld&is_l).any(1),
                  ((wld&bow).any(1)&arrow.any(1))|((wld&xbow).any(1)&bolt.any(1))],1).astype(np.float32)
INV_M = np.ones((N,6), np.float32)
INV_NAMES = ['n_items','has_lnchr','has_ammo','pair','wld_lnchr','lnc_rdy']
INV_BIN = [False, True, True, True, True, True]

val_mask = np.zeros(N, bool); off = 0
for p in parts:
    n = len(p[0]); val_mask[off+int(n*.8):off+n] = True; off += n
tr, va = np.arange(N)[~val_mask], np.arange(N)[val_mask]
GV = 6000
gl = np.clip(gl, 0, GV-1); CROP = np.clip(CROP, 0, GV-1)

def rel_grid(B, R, C, hxy):
    yy, xx = torch.meshgrid(torch.arange(R, device=dev), torch.arange(C, device=dev), indexing='ij')
    dy = (yy.unsqueeze(0) - hxy[:,1].view(-1,1,1)); dx = (xx.unsqueeze(0) - hxy[:,0].view(-1,1,1))
    ch = torch.maximum(dx.abs(), dy.abs())
    return torch.stack([dy/10.0, dx/20.0, ch/15.0], -1)

class EgoAttn(nn.Module): # baseline (round-6 winner)
    def __init__(s, heads=4, deep=False):
        super().__init__(); s.emb = nn.Embedding(GV, 29); s.heads = heads
        vin = 32
        s.v = nn.Sequential(nn.Linear(vin,128), nn.ReLU(), nn.Linear(128,128)) if deep else nn.Linear(vin,128)
        s.a = nn.Linear(vin, heads)
    def forward(s, g, hxy):
        B, R, C = g.shape
        t = torch.cat([s.emb(g), rel_grid(B,R,C,hxy)], -1).flatten(1,2)
        v = torch.relu(s.v(t)).view(B,-1,s.heads,128//s.heads)
        a = torch.softmax(s.a(t), 1)
        return (v * a.unsqueeze(-1)).sum(1).flatten(1)

class CropFlat(nn.Module): # analog of the current local branch
    def __init__(s):
        super().__init__(); s.emb = nn.Embedding(GV, 16)
        s.f = nn.Sequential(nn.Linear(121*16, 256), nn.ReLU(), nn.Linear(256,128), nn.ReLU())
    def forward(s, c, _):
        return s.f(s.emb(c).flatten(1))

class CropConv(nn.Module):
    def __init__(s):
        super().__init__(); s.emb = nn.Embedding(GV, 16)
        s.c1 = nn.Conv2d(16,32,3,padding=1); s.c2 = nn.Conv2d(32,32,3,padding=1)
        s.f = nn.Linear(32*121, 128)
    def forward(s, c, _):
        e = s.emb(c).permute(0,3,1,2)
        h = torch.relu(s.c2(torch.relu(s.c1(e))))
        return torch.relu(s.f(h.flatten(1)))

class CropAttn(nn.Module):
    def __init__(s):
        super().__init__(); s.emb = nn.Embedding(GV, 29); s.v = nn.Linear(32,128); s.a = nn.Linear(32,4)
        yy, xx = torch.meshgrid(torch.arange(11), torch.arange(11), indexing='ij')
        ch = torch.maximum((xx-5).abs(), (yy-5).abs())
        s.register_buffer('rel', torch.stack([(yy-5)/5., (xx-5)/5., ch/5.], -1).float())
    def forward(s, c, _):
        B = c.shape[0]
        t = torch.cat([s.emb(c), s.rel.unsqueeze(0).expand(B,-1,-1,-1)], -1).flatten(1,2)
        v = torch.relu(s.v(t)).view(B,-1,4,32)
        a = torch.softmax(s.a(t), 1)
        return (v * a.unsqueeze(-1)).sum(1).flatten(1)

def inv_feats(st):
    return torch.log1p(st.abs().float()) / 4.0

class InvAttn8(nn.Module):
    def __init__(s):
        super().__init__(); s.emb = nn.Embedding(GV, 24); s.st = nn.Linear(8,8)
        s.v = nn.Linear(32,128); s.a = nn.Linear(32,8)
    def forward(s, iv, st):
        t = torch.cat([s.emb(torch.clamp(iv,0,GV-1)), torch.relu(s.st(inv_feats(st)))], -1)
        v = torch.relu(s.v(t)).view(iv.shape[0],-1,8,16)
        a = torch.softmax(s.a(t), 1)
        return (v * a.unsqueeze(-1)).sum(1).flatten(1)

class InvSelfAttn(nn.Module): # cross-slot interactions for conjunctions
    def __init__(s):
        super().__init__(); s.emb = nn.Embedding(GV, 24); s.st = nn.Linear(8,8)
        s.mha = nn.MultiheadAttention(32, 4, batch_first=True)
        s.v = nn.Linear(32,128); s.a = nn.Linear(32,4)
    def forward(s, iv, st):
        t = torch.cat([s.emb(torch.clamp(iv,0,GV-1)), torch.relu(s.st(inv_feats(st)))], -1)
        t = t + s.mha(t, t, t)[0]
        v = torch.relu(s.v(t)).view(iv.shape[0],-1,4,32)
        a = torch.softmax(s.a(t), 1)
        return (v * a.unsqueeze(-1)).sum(1).flatten(1)

def auc(y, p):
    o = np.argsort(p); r = np.empty(len(p)); r[o] = np.arange(1, len(p)+1)
    pos = y > 0.5
    if pos.sum() < 20 or (~pos).sum() < 20: return float('nan')
    return (r[pos].mean() - (pos.sum()+1)/2) / (~pos).sum()

def run(name, net, X1, X2, Y, M, names, isbin, epochs):
    net = net.to(dev); head = nn.Linear(128, Y.shape[1]).to(dev)
    opt = torch.optim.Adam(list(net.parameters())+list(head.parameters()), lr=1.5e-3)
    x1 = torch.from_numpy(X1).to(dev); x2 = torch.from_numpy(X2).to(dev) if X2 is not None else None
    y = torch.from_numpy(Y).to(dev); m = torch.from_numpy(M).to(dev)
    for ep in range(epochs):
        perm = torch.from_numpy(np.random.permutation(tr)).to(dev)
        for i in range(0, len(perm), 4096):
            b = perm[i:i+4096]
            p = head(net(x1[b], x2[b] if x2 is not None else None))
            mb = m[b]
            loss = (torch.nn.functional.smooth_l1_loss(p, y[b], reduction='none')*mb).sum()/mb.sum()
            opt.zero_grad(); loss.backward(); opt.step()
    def evl(ix):
        with torch.no_grad():
            return torch.cat([head(net(x1[ix[i:i+8192]], x2[ix[i:i+8192]] if x2 is not None else None))
                              for i in range(0, len(ix), 8192)]).cpu().numpy()
    vi = torch.from_numpy(va).to(dev)
    p = evl(vi)
    out = [name]
    for k in range(Y.shape[1]):
        mv = M[va][:,k] > 0
        if mv.sum() < 100: out.append('-'); continue
        yv, pv = Y[va][mv,k], p[mv,k]
        if isbin[k]:
            out.append(f'{auc(yv,pv):.3f}a')
        else:
            out.append(f'{1 - ((yv-pv)**2).sum()/max(((yv-yv.mean())**2).sum(),1e-9):.2f}')
    print(('{:10s}'+'{:>9s}'*(len(out)-1)).format(*out), flush=True)

hxy = bl.astype(np.int64)
print(('{:10s}'+'{:>9s}'*6).format('GEO', *GEO_NAMES), flush=True)
run('egoattn', EgoAttn(4), gl, hxy, GEO_Y, GEO_M, GEO_NAMES, GEO_BIN, EP_GEO)
run('egoattn8d', EgoAttn(8, deep=True), gl, hxy, GEO_Y, GEO_M, GEO_NAMES, GEO_BIN, EP_GEO)
print(('{:10s}'+'{:>9s}'*11).format('LOCAL', *LOC_NAMES), flush=True)
run('cropflat', CropFlat(), CROP, hxy, LOC_Y, LOC_M, LOC_NAMES, LOC_BIN, EP_LOC)
run('cropconv', CropConv(), CROP, hxy, LOC_Y, LOC_M, LOC_NAMES, LOC_BIN, EP_LOC)
run('cropattn', CropAttn(), CROP, hxy, LOC_Y, LOC_M, LOC_NAMES, LOC_BIN, EP_LOC)
print(('{:10s}'+'{:>9s}'*6).format('INV', *INV_NAMES), flush=True)
run('invattn8', InvAttn8(), inv, ist, INV_Y, INV_M, INV_NAMES, INV_BIN, EP_INV)
run('invselfat', InvSelfAttn(), inv, ist, INV_Y, INV_M, INV_NAMES, INV_BIN, EP_INV)
