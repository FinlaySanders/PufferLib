# GPU branch lab v2: architecture x target factory. Geometry targets (static,
# monster-derivable, hostile w/ info gap) on the glyph map; inventory targets
# incl. conjunctions (launcher<->ammo match) on the inv block. R2 val/train
# per cell; per-arch flushed progress.
import json, sys, numpy as np, torch, torch.nn as nn
dev = 'cuda'
torch.manual_seed(0)

L = json.load(open('/tmp/aux_layout.json'))
OBS, OE, AUX, ROWS, COLS = L['obs_size'], L['off_extra'], L['aux_idx'], L['rows'], L['cols']
OFF_INV, OFF_INVST = L['off_inv'], L['off_invst']
FILES = ['/puffertank/auxdata/farmer.bin', '/puffertank/auxdata/merchant.bin', '/puffertank/auxdata/digger.bin']
PER = int(sys.argv[1]) if len(sys.argv) > 1 else 65000
EPOCHS = int(sys.argv[2]) if len(sys.argv) > 2 else 20

def load(f, n):
    m = np.memmap(f, dtype=np.uint8, mode='r')
    n = min(n, len(m) // OBS)
    m = m[:n * OBS].reshape(n, OBS)
    gl = m[:, :ROWS * COLS * 2].view(np.int16).reshape(n, ROWS, COLS).astype(np.int64)
    bl = m[:, L['off_blstats']:L['off_blstats'] + 8].view(np.int32).reshape(n, 2).astype(np.int64)
    ax = m[:, OE + 4 * AUX:OE + 4 * (AUX + 10)].view(np.int32).reshape(n, 10).astype(np.float32)
    inv = m[:, OFF_INV:OFF_INV + 55 * 2].view(np.int16).reshape(n, 55).astype(np.int64)
    ist = m[:, OFF_INVST:OFF_INVST + 55 * 8].reshape(n, 55, 8).astype(np.int64)
    return gl, bl, ax, inv, ist

parts = [load(f, PER) for f in FILES]
gl = np.concatenate([p[0] for p in parts]); bl = np.concatenate([p[1] for p in parts])
ax = np.concatenate([p[2] for p in parts]); inv = np.concatenate([p[3] for p in parts])
ist = np.concatenate([p[4] for p in parts])
N = len(gl)
print(f'frames {N}', flush=True)

# ---- targets ----
def mon_targets(gl, bl):
    ism = ((gl >= 0) & (gl < 381)) | ((gl >= 762) & (gl < 1144))
    out = np.zeros((len(gl), 3), np.float32)
    for i in range(len(gl)):
        rr, cc = np.nonzero(ism[i])
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

GEO_Y = np.stack([
    ax[:, 1] / 40, ax[:, 2] / 10,          # ds_dx ds_dy   (mask: ds_seen)
    MT[:, 0] / 20, MT[:, 1] / 10, MT[:, 2] / 15,  # nm_dx nm_dy nm_dist (mask: nm vis, ones)
    ax[:, 4] / 20, ax[:, 5] / 10,          # nh_dx nh_dy   (mask: hostile vis; info-gap cells)
    np.minimum(ax[:, 6], 16) / 16,         # nh_cnt
], 1).astype(np.float32)
GEO_NAMES = ['ds_dx','ds_dy','nm_dx','nm_dy','nm_dist','nh_dx','nh_dy','nh_cnt']
ones = np.ones(N, np.float32)
GEO_M = np.stack([ax[:,0], ax[:,0], (MT[:,2]<15), (MT[:,2]<15), ones,
                  (ax[:,3]<15), (ax[:,3]<15), ones], 1).astype(np.float32)

# inventory targets from otyps (glyph-OBJ_OFF): launchers 65-70, arrows 1-6 + 445/446
OBJ_OFF = 1906
ot = np.where(inv > 0, inv - OBJ_OFF, -1)
is_launcher = (ot >= 65) & (ot <= 70)
is_ammo = ((ot >= 1) & (ot <= 6)) | (ot == 445) | (ot == 446)
# match groups: bows(66-68?)<->arrows(1-4), crossbow(70)<->bolts(5-6), sling(65)<->stones
bow = (ot >= 66) & (ot <= 69); arrow = (ot >= 1) & (ot <= 4)
xbow = ot == 70; bolt = (ot >= 5) & (ot <= 6)
wielded = (ist[:, :, 5] & 2) > 0
INV_Y = np.stack([
    (inv > 0).sum(1) / 55.0,                       # n_items
    is_launcher.any(1).astype(float),              # has_launcher
    is_ammo.any(1).astype(float),                  # has_ammo
    ((bow.any(1) & arrow.any(1)) | (xbow.any(1) & bolt.any(1))).astype(float),  # MATCHED pair
    (wielded & is_launcher).any(1).astype(float),  # wielding a launcher
    ((wielded & bow).any(1) & arrow.any(1) | (wielded & xbow).any(1) & bolt.any(1)).astype(float), # lnc bit
], 1).astype(np.float32)
INV_NAMES = ['n_items','has_lnchr','has_ammo','pair_match','wield_lnchr','lnc_ready']
INV_M = np.ones((N, 6), np.float32)

val_mask = np.zeros(N, bool); off = 0
for p in parts:
    n = len(p[0]); val_mask[off + int(n * .8):off + n] = True; off += n
tr, va = np.arange(N)[~val_mask], np.arange(N)[val_mask]
GV = 6000
gl = np.clip(gl, 0, GV - 1)

class PatchMax(nn.Module):
    def __init__(s, H=128):
        super().__init__(); s.emb = nn.Embedding(GV, 32); s.tok = nn.Linear(800, 16); s.proj = nn.Linear(18, H)
        xy = torch.stack(torch.meshgrid(torch.arange(4), torch.arange(12), indexing='ij'), -1)
        s.register_buffer('xy', xy.reshape(-1, 2).float() / torch.tensor([4., 12.]))
    def forward(s, g, hxy):
        B = g.shape[0]
        e = s.emb(g[:, :20, :60]).reshape(B, 4, 5, 12, 5, 32).permute(0, 1, 3, 2, 4, 5).reshape(B, 48, 800)
        t = torch.relu(s.tok(e))
        t = torch.cat([t, s.xy.unsqueeze(0).expand(B, -1, -1)], -1)
        return torch.relu(s.proj(t)).max(1).values

class EgoTok(nn.Module):
    def __init__(s, H=128):
        super().__init__(); s.emb = nn.Embedding(GV, 30); s.proj = nn.Linear(32, H)
    def forward(s, g, hxy):
        B, R, C = g.shape
        e = s.emb(g)
        yy, xx = torch.meshgrid(torch.arange(R, device=dev), torch.arange(C, device=dev), indexing='ij')
        rel = torch.stack([(yy.unsqueeze(0) - hxy[:, 1].view(-1, 1, 1)) / 10.0,
                           (xx.unsqueeze(0) - hxy[:, 0].view(-1, 1, 1)) / 20.0], -1)
        t = torch.cat([e, rel], -1)
        return torch.relu(s.proj(t)).flatten(1, 2).max(1).values

class EgoTok2(nn.Module): # 2-layer token mlp (composition depth)
    def __init__(s, H=128):
        super().__init__(); s.emb = nn.Embedding(GV, 30)
        s.f1 = nn.Linear(32, 64); s.f2 = nn.Linear(64, H)
    def forward(s, g, hxy):
        B, R, C = g.shape
        e = s.emb(g)
        yy, xx = torch.meshgrid(torch.arange(R, device=dev), torch.arange(C, device=dev), indexing='ij')
        rel = torch.stack([(yy.unsqueeze(0) - hxy[:, 1].view(-1, 1, 1)) / 10.0,
                           (xx.unsqueeze(0) - hxy[:, 0].view(-1, 1, 1)) / 20.0], -1)
        t = torch.cat([e, rel], -1)
        return torch.relu(s.f2(torch.relu(s.f1(t)))).flatten(1, 2).max(1).values

class EgoAttn(nn.Module): # attention pool: select-and-read (logits=learned, values carry dx)
    def __init__(s, H=128):
        super().__init__(); s.emb = nn.Embedding(GV, 30)
        s.v = nn.Linear(32, H); s.a = nn.Linear(32, 4) # 4 attention heads
    def forward(s, g, hxy):
        B, R, C = g.shape
        e = s.emb(g)
        yy, xx = torch.meshgrid(torch.arange(R, device=dev), torch.arange(C, device=dev), indexing='ij')
        rel = torch.stack([(yy.unsqueeze(0) - hxy[:, 1].view(-1, 1, 1)) / 10.0,
                           (xx.unsqueeze(0) - hxy[:, 0].view(-1, 1, 1)) / 20.0], -1)
        t = torch.cat([e, rel], -1).flatten(1, 2)
        v = torch.relu(s.v(t)).view(B, -1, 4, 32)
        a = torch.softmax(s.a(t), 1)
        return (v * a.unsqueeze(-1)).sum(1).flatten(1)

class InvPool(nn.Module): # replica of the current inventory branch shape
    def __init__(s, H=128):
        super().__init__(); s.emb = nn.Embedding(GV, 24); s.st = nn.Linear(8, 8); s.proj = nn.Linear(32, H)
    def forward(s, iv, st):
        e = s.emb(torch.clamp(iv, 0, GV - 1))
        t = torch.cat([e, torch.relu(s.st(torch.log1p(st.abs()) / 4.0))], -1)
        return torch.relu(s.proj(t)).max(1).values

class InvAttn(nn.Module): # single-head attention pool over slots
    def __init__(s, H=128):
        super().__init__(); s.emb = nn.Embedding(GV, 24); s.st = nn.Linear(8, 8)
        s.kv = nn.Linear(32, H); s.q = nn.Parameter(torch.randn(H) * .05)
    def forward(s, iv, st):
        e = s.emb(torch.clamp(iv, 0, GV - 1))
        t = torch.relu(s.kv(torch.cat([e, torch.relu(s.st(torch.log1p(st.abs()) / 4.0))], -1)))
        a = torch.softmax((t * s.q).sum(-1) / 8.0, 1)
        return (t * a.unsqueeze(-1)).sum(1)

def run(name, net, X1, X2, Y, M, names):
    net = net.to(dev); head = nn.Linear(128, Y.shape[1]).to(dev)
    opt = torch.optim.Adam(list(net.parameters()) + list(head.parameters()), lr=1.5e-3)
    x1 = torch.from_numpy(X1).to(dev); x2 = torch.from_numpy(X2).float().to(dev) if X2 is not None else None
    y = torch.from_numpy(Y).to(dev); m = torch.from_numpy(M).to(dev)
    for ep in range(EPOCHS):
        perm = torch.from_numpy(np.random.permutation(tr)).to(dev)
        for i in range(0, len(perm), 4096):
            b = perm[i:i + 4096]
            p = head(net(x1[b], x2[b] if x2 is not None else None))
            mb = m[b]
            loss = (torch.nn.functional.smooth_l1_loss(p, y[b], reduction='none') * mb).sum() / mb.sum()
            opt.zero_grad(); loss.backward(); opt.step()
    def evl(ix):
        with torch.no_grad():
            return torch.cat([head(net(x1[ix[i:i+8192]], x2[ix[i:i+8192]] if x2 is not None else None))
                              for i in range(0, len(ix), 8192)]).cpu().numpy()
    ti = torch.from_numpy(tr[:30000]).to(dev); vi = torch.from_numpy(va).to(dev)
    p, pt = evl(vi), evl(ti)
    out = [name]
    for k in range(Y.shape[1]):
        mv = M[va][:, k] > 0; mt = M[tr[:30000]][:, k] > 0
        if mv.sum() < 100: out.append('-'); continue
        r2 = 1 - ((Y[va][mv, k] - p[mv, k])**2).sum() / max(((Y[va][mv, k] - Y[va][mv, k].mean())**2).sum(), 1e-9)
        r2t = 1 - ((Y[tr[:30000]][mt, k] - pt[mt, k])**2).sum() / max(((Y[tr[:30000]][mt, k] - Y[tr[:30000]][mt, k].mean())**2).sum(), 1e-9)
        out.append(f'{r2:.2f}/{r2t:.2f}')
    print(('{:10s}' + '{:>12s}' * (len(out) - 1)).format(*out), flush=True)

print(('{:10s}' + '{:>12s}' * 8).format('GEO(v/t)', *GEO_NAMES), flush=True)
hxy = bl.astype(np.int64)
for nm, cls in [('egotok2', EgoTok2), ('egoattn', EgoAttn)]:
    run(nm, cls(), gl, hxy, GEO_Y, GEO_M, GEO_NAMES)
print(('{:10s}' + '{:>12s}' * 6).format('INV(v/t)', *INV_NAMES), flush=True)
for nm, cls in [('invpool', InvPool), ('invattn', InvAttn)]:
    run(nm, cls(), inv, ist, INV_Y, INV_M, INV_NAMES)
