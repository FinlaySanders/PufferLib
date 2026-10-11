# Branch lab: supervised sub-problems for encoder branches. Loads mixed
# specialist rollouts (obs with NH_AUX targets embedded), trains candidate
# branch architectures against the spec targets, reports R2/acc per
# (arch, target). CPU-friendly; small models.
import json, sys, numpy as np, torch, torch.nn as nn
torch.set_num_threads(4)
torch.manual_seed(0)

L = json.load(open('/tmp/aux_layout.json'))
OBS, OE, AUX, ROWS, COLS = L['obs_size'], L['off_extra'], L['aux_idx'], L['rows'], L['cols']
FILES = ['/puffertank/auxdata/farmer.bin', '/puffertank/auxdata/merchant.bin', '/puffertank/auxdata/digger.bin']
PER = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
EPOCHS = int(sys.argv[2]) if len(sys.argv) > 2 else 4

def load(f, n):
    m = np.memmap(f, dtype=np.uint8, mode='r')
    N = len(m) // OBS
    n = min(n, N)
    m = m[:n * OBS].reshape(n, OBS)
    gl = m[:, :ROWS * COLS * 2].view(np.int16).reshape(n, ROWS, COLS).astype(np.int64)
    bl = m[:, L['off_blstats']:L['off_blstats'] + 8].view(np.int32).reshape(n, 2)
    ax = m[:, OE + 4 * AUX:OE + 4 * (AUX + 10)].view(np.int32).reshape(n, 10)
    return gl, bl.astype(np.int64), ax.astype(np.float32)

gls, bls, axs = zip(*[load(f, PER) for f in FILES])
gl = np.concatenate(gls); bl = np.concatenate(bls); ax = np.concatenate(axs)
N = len(gl)
print(f'frames {N}  (aux sample: {ax[100]})')
# targets: 0 ds_seen 1 ds_dx 2 ds_dy 3 nh_dist 4 nh_dx 5 nh_dy 6 nh_count 7 nit 8 food 9 wcl
Y = np.stack([ax[:, 1] / 40.0, ax[:, 2] / 10.0, ax[:, 4] / 20.0, ax[:, 5] / 10.0,
              ax[:, 3] / 15.0, np.minimum(ax[:, 6], 16) / 16.0], 1).astype(np.float32)
YSEEN = ax[:, 0].astype(np.float32)      # ds visible bit (masks ds targets)
YHOST = (ax[:, 3] < 15).astype(np.float32)  # hostile-visible (masks nh targets)
GVOCAB = 6000
gl = np.clip(gl, 0, GVOCAB - 1)

# nearest-ANY-monster targets from glyphs (fully input-derivable: the clean
# architecture test; the peaceful-filtered engine targets are only partially
# observable from glyphs)
def mon_targets(gl, bl):
    N = len(gl)
    ism = ((gl >= 0) & (gl < 381)) | ((gl >= 762) & (gl < 1144))
    out = np.zeros((N, 3), np.float32)
    for i in range(N):
        rr, cc = np.nonzero(ism[i])
        hx, hy = bl[i, 0], bl[i, 1]
        self_m = (cc == hx) & (rr == hy)
        rr, cc = rr[~self_m], cc[~self_m]
        if len(rr) == 0:
            out[i] = (0, 0, 15); continue
        dx, dy = cc - hx, rr - hy
        d = np.maximum(np.abs(dx), np.abs(dy))
        j = d.argmin()
        out[i] = (dx[j], dy[j], min(d[j], 15))
    return out
MT = np.concatenate([mon_targets(g, b) for g, b in zip(gls, bls)])
Y = np.concatenate([Y, np.stack([MT[:, 0] / 20.0, MT[:, 1] / 10.0, MT[:, 2] / 15.0], 1)], 1).astype(np.float32)
YMON = (MT[:, 2] < 15).astype(np.float32)

# per-policy temporal split (last 20% of each file = val)
idx = np.arange(N); val_mask = np.zeros(N, bool)
off = 0
for g in gls:
    n = len(g); val_mask[off + int(n * 0.8):off + n] = True; off += n
tr, va = idx[~val_mask], idx[val_mask]

class PatchMax(nn.Module): # replica-shape of the current global branch
    # 20x60 crop -> 4x12 grid of 5x5 patches -> 16-d token + xy -> proj -> channel max
    def __init__(s, H=128):
        super().__init__()
        s.emb = nn.Embedding(GVOCAB, 32)
        s.tok = nn.Linear(25 * 32, 16)
        s.proj = nn.Linear(18, H)
        xy = torch.stack(torch.meshgrid(torch.arange(4), torch.arange(12), indexing='ij'), -1)
        s.register_buffer('xy', xy.reshape(-1, 2).float() / torch.tensor([4., 12.]))
    def forward(s, g):
        B = g.shape[0]
        e = s.emb(g[:, :20, :60].contiguous()).reshape(B, 4, 5, 12, 5, 32)
        e = e.permute(0, 1, 3, 2, 4, 5).reshape(B, 48, 25 * 32)
        t = torch.relu(s.tok(e))
        t = torch.cat([t, s.xy.unsqueeze(0).expand(B, -1, -1)], -1)
        h = torch.relu(s.proj(t))
        return h.max(1).values

class ConvNet(nn.Module):
    def __init__(s, H=128):
        super().__init__()
        s.emb = nn.Embedding(GVOCAB, 16)
        s.c1 = nn.Conv2d(16, 32, 5, stride=2, padding=2)
        s.c2 = nn.Conv2d(32, 32, 3, stride=2, padding=1)
        s.fc = nn.Linear(32 * 6 * 20, H)
    def forward(s, g):
        e = s.emb(g).permute(0, 3, 1, 2)
        h = torch.relu(s.c2(torch.relu(s.c1(e))))
        return torch.relu(s.fc(h.flatten(1)))

class Tokens(nn.Module): # per-cell tokens for nonzero-ish cells, max-pool with xy
    def __init__(s, H=128):
        super().__init__()
        s.emb = nn.Embedding(GVOCAB, 30)
        s.proj = nn.Linear(32, H)
    def forward(s, g):
        B, R, C = g.shape
        e = s.emb(g)
        yy, xx = torch.meshgrid(torch.arange(R), torch.arange(C), indexing='ij')
        xy = torch.stack([yy / R, xx / C], -1).float().to(g.device)
        t = torch.cat([e, xy.unsqueeze(0).expand(B, -1, -1, -1)], -1)
        return torch.relu(s.proj(t)).flatten(1, 2).max(1).values

class EgoTokens(nn.Module): # per-cell emb + HERO-RELATIVE dx,dy (v3.2 ring idea)
    def __init__(s, H=128):
        super().__init__()
        s.emb = nn.Embedding(GVOCAB, 30)
        s.proj = nn.Linear(32, H)
    def forward(s, g, hxy):
        B, R, C = g.shape
        e = s.emb(g)
        yy, xx = torch.meshgrid(torch.arange(R), torch.arange(C), indexing='ij')
        yy = yy.unsqueeze(0).float() - hxy[:, 1].view(-1, 1, 1)
        xx = xx.unsqueeze(0).float() - hxy[:, 0].view(-1, 1, 1)
        rel = torch.stack([yy / 10.0, xx / 20.0], -1)
        t = torch.cat([e, rel], -1)
        return torch.relu(s.proj(t)).flatten(1, 2).max(1).values

def run(name, net):
    head = nn.Linear(128, 9)
    opt = torch.optim.Adam(list(net.parameters()) + list(head.parameters()), lr=1e-3)
    g_t = torch.from_numpy(gl); y_t = torch.from_numpy(Y); bl_t = torch.from_numpy(bl.astype(np.float32))
    ms = torch.from_numpy(np.stack([YSEEN, YSEEN, YHOST, YHOST, np.ones(N, np.float32), np.ones(N, np.float32), YMON, YMON, np.ones(N, np.float32)], 1))
    for ep in range(EPOCHS):
        perm = np.random.permutation(tr)
        tot = 0
        for i in range(0, len(perm), 512):
            b = perm[i:i + 512]
            p = head(net(g_t[b], bl_t[b]) if getattr(net, 'needs_hxy', False) else net(g_t[b]))
            m = ms[b]
            loss = (torch.nn.functional.smooth_l1_loss(p, y_t[b], reduction='none') * m).sum() / m.sum()
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss)
    def evl(ix):
        with torch.no_grad():
            ps = []
            for i in range(0, len(ix), 2048):
                bb = ix[i:i + 2048]
                ps.append(head(net(g_t[bb], bl_t[bb]) if getattr(net, 'needs_hxy', False) else net(g_t[bb])))
            return torch.cat(ps).numpy()
    p = evl(va)
    ptr = evl(tr[:20000])
    out = [name]
    for k in range(9):
        m = ms[va][:, k].numpy() > 0
        mt = ms[tr[:20000]][:, k].numpy() > 0
        if m.sum() < 100: out.append('-'); continue
        yv, pv = Y[va][m, k], p[m, k]
        yt, pt = Y[tr[:20000]][mt, k], ptr[mt, k]
        r2 = 1 - ((yv - pv) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
        r2t = 1 - ((yt - pt) ** 2).sum() / ((yt - yt.mean()) ** 2).sum()
        out.append(f'{r2:.2f}/{r2t:.2f}')
    print(('{:9s}' + '{:>12s}' * 9).format(out[0], *out[1:]), flush=True)

print(('{:9s}' + '{:>12s}' * 9).format('arch(v/t)', 'ds_dx', 'ds_dy', 'nh_dx', 'nh_dy', 'nh_dist', 'nh_cnt', 'nm_dx', 'nm_dy', 'nm_dist'), flush=True)
ego = EgoTokens(); ego.needs_hxy = True
run('egotok', ego)
run('tokens', Tokens())
