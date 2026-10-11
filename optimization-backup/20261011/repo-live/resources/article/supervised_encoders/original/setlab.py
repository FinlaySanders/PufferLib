# Set-encoder architecture race for inventory-style encoding.
# Regimes: real (production dumps, cross-seed val) | synth (calibrated generator,
# controlled labels, size-generalization + duplication diagnostics).
# Protocol: budget-parity zoo, per-arch lr grid chosen on train-val loss,
# 3-seed medians, shuffle floor. Results append to setlab_{regime}.jsonl.
import numpy as np, torch, torch.nn as nn, time, json, sys, os
dev = 'cuda'
REGIME = sys.argv[1] if len(sys.argv) > 1 else 'synth'
OUT = f'/tmp/claude-0/-puffertank-pufferlib/a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6/scratchpad/setlab_{REGIME}.jsonl'
done = set()
if os.path.exists(OUT):
    for l in open(OUT): done.add(json.loads(l)['key'])

S, GV, PAD = 55, 6000, 5976
TN  = ['has_lnc','has_ammo','has_bles','has_bw','pair','wldweap',
       'n_items','n_food','n_weap','n_curse','n_bles','ammo_ct','n_bwep','n_cw',
       'max_ench','bw_ench','wld_ench','min_erow']
BIN = set(range(6)); NT = len(TN)

# ---------------- real regime ----------------
def load_real():
    def parse(f):
        r = np.fromfile(f, dtype=np.uint8).reshape(-1, 810)
        N = len(r)
        d = {}
        d['gl'] = r[:,0:110].copy().view(np.uint16).reshape(N,S).astype(np.int64)
        d['st'] = r[:,110:550].reshape(N,S,8).astype(np.int64)
        d['sts'] = r[:,110:550].copy().view(np.int8).reshape(N,S,8).astype(np.int64)
        d['itr'] = r[:,550:660].copy().view(np.uint16).reshape(N,S).astype(np.int64)
        d['scl'] = r[:,660:715].astype(np.int64)
        d['sfl'] = r[:,715:770].astype(np.int64)
        d['si'] = r[:,770:802].copy().view(np.int32).reshape(N,8)
        return d
    tr = [parse('/tmp/inv_lab1b_s702.bin'), parse('/tmp/inv_s702_long.bin')]
    va = parse('/tmp/inv_lab1b_s701.bin')
    cat = {k: np.concatenate([t[k] for t in tr]) for k in tr[0]}
    return cat, va

def real_targets(d):
    N = len(d['gl'])
    occ = d['gl'] != PAD
    st, sts, scl, sfl, si = d['st'], d['sts'], d['scl'], d['sfl'], d['si']
    buc3 = (st[:,:,0]==3)&occ; buc1 = (st[:,:,0]==1)&occ
    weap = (scl==2)&occ
    spk = sts[:,:,1] != -128
    spe = np.where(spk, sts[:,:,1], 0)
    wield = ((st[:,:,5]>>1)&1).astype(bool)&occ
    worn = (st[:,:,5]&1).astype(bool)&occ
    T = np.zeros((N,NT), np.float32); M = np.ones((N,NT), np.float32)
    T[:,0] = np.array([(x&2).any() for x in sfl]); T[:,1] = np.array([(x&1).any() for x in sfl])
    T[:,2] = buc3.any(1); T[:,3] = (buc3&weap).any(1)
    T[:,4] = (si[:,0]&1)>0; T[:,5] = si[:,2]==2
    T[:,6] = np.minimum(occ.sum(1),30)/30; T[:,7] = np.minimum(si[:,5],8)/8
    T[:,8] = np.minimum(si[:,4],10)/10; T[:,9] = np.minimum(si[:,6],5)/5
    T[:,10] = np.minimum(buc3.sum(1),8)/8
    T[:,11] = np.minimum(np.where(sfl&1>0, st[:,:,2],0).sum(1),40)/40
    T[:,12] = np.minimum((buc3&weap).sum(1),4)/4
    T[:,13] = np.minimum((buc1&worn).sum(1),3)/3
    T[:,14] = np.where(spk&occ, spe, -9).max(1).clip(-3,6)/6
    bw = np.where(weap&spk, spe, -9).max(1); M[:,15] = (weap&spk).any(1); T[:,15] = bw.clip(-3,6)/6
    we = np.where(wield&spk, spe, 0).sum(1); M[:,16] = (wield&spk).any(1); T[:,16] = we.clip(-3,6)/6
    er = np.where(worn, st[:,:,3], 9).min(1); M[:,17] = worn.any(1); T[:,17] = np.where(M[:,17]>0, er, 0)/3
    return T, M, occ

def real_inputs(d):
    N = len(d['gl'])
    occ = (d['gl'] != PAD)
    sts, st = d['sts'], d['st']
    SF = np.zeros((N,S,12), np.float32)
    SF[:,:,0] = occ
    for c in range(4): SF[:,:,1+c] = st[:,:,0]==c
    spk = sts[:,:,1] != -128
    SF[:,:,5] = spk; SF[:,:,6] = np.where(spk, sts[:,:,1],0)*0.1
    SF[:,:,7] = np.minimum(st[:,:,2],30)/30
    SF[:,:,8] = st[:,:,3]/3; SF[:,:,9] = st[:,:,4]/3
    SF[:,:,10] = st[:,:,5]&1; SF[:,:,11] = (st[:,:,5]>>1)&1
    return np.clip(d['gl'],0,GV-1), np.clip(d['itr'],0,GV-1), SF, occ.astype(np.float32), np.clip(d['scl'],0,18)

# ---------------- synthetic regime ----------------
CLS_P = np.array([.193,.189,.021,.0003,.096,.153,.099,.117,.013,.039,.021,.057,.0003])
CLS_P = CLS_P/CLS_P.sum()  # classes 2..14 engine-coded order
CLS_ID = np.arange(2,15)
NTYPE = 40
LAUNCH_T = [0,1,2]; AMMO_T = [3,4,5,6,7]  # weapon-class type ids; match: L0<->A3, L1<->A4, L2<->A5
MATCH = {0:3, 1:4, 2:5}
def gen_synth(N, rng, nlo=3, nhi=40):
    n = np.clip(rng.normal(18,7,N).astype(int), nlo, nhi)
    gl = np.full((N,S), PAD, np.int64); itr = np.full((N,S), PAD, np.int64)
    cls = np.zeros((N,S), np.int64); typ = np.zeros((N,S), np.int64)
    st = np.zeros((N,S,8), np.int64)  # buc,spe,quan,ero1,ero2,flags,tk
    occm = np.zeros((N,S), bool)
    for i in range(N):
        k = n[i]
        occm[i,:k] = True
        c = CLS_ID[rng.choice(13, k, p=CLS_P)]
        t = rng.integers(0, NTYPE, k)
        z = rng.zipf(1.6, k) % NTYPE  # popularity skew
        t = np.where(rng.random(k)<.6, z, t)
        cls[i,:k] = c; typ[i,:k] = t
        gl[i,:k] = c*300 + t
        buc = rng.choice(4, k, p=[.62,.06,.22,.10])
        st[i,:k,0] = buc
        spk = rng.random(k) < .45
        st[i,:k,1] = np.where(spk, rng.integers(-3,6,k), -128)
        isammo = (c==2) & np.isin(t, AMMO_T)
        st[i,:k,2] = np.where(isammo, rng.geometric(.12,k).clip(1,40), 1)
        st[i,:k,3] = rng.choice(4, k, p=[.8,.1,.06,.04])
        tk = rng.random(k) < .55
        st[i,:k,6] = tk
        itr[i,:k] = np.where(tk, gl[i,:k], PAD)
        wpos = np.where(c==2)[0]
        if len(wpos) and rng.random()<.8: st[i,wpos[0],5] |= 2
        apos = np.where(c==3)[0]
        for p in apos[:4]:
            if rng.random()<.5: st[i,p,5] |= 1
    return dict(gl=gl, itr=itr, cls=cls, typ=typ, st=st, occ=occm, n=n)

def synth_targets(d):
    N = len(d['gl'])
    occ, st, cls, typ = d['occ'], d['st'], d['cls'], d['typ']
    buc3 = (st[:,:,0]==3)&occ; buc1 = (st[:,:,0]==1)&occ
    weap = (cls==2)&occ; food = (cls==7)&occ
    lnc = weap & np.isin(typ, LAUNCH_T); ammo = weap & np.isin(typ, AMMO_T)
    spk = st[:,:,1] != -128; spe = np.where(spk, st[:,:,1], 0)
    wield = ((st[:,:,5]>>1)&1).astype(bool)&occ; worn = (st[:,:,5]&1).astype(bool)&occ
    pair = np.zeros(N, bool)
    for l,a in MATCH.items():
        pair |= (weap&(typ==np.int64(l))&np.isin(typ,[l])&lnc).any(1) & (weap&(typ==a)).any(1)
    T = np.zeros((N,NT), np.float32); M = np.ones((N,NT), np.float32)
    T[:,0] = lnc.any(1); T[:,1] = ammo.any(1)
    T[:,2] = buc3.any(1); T[:,3] = (buc3&weap).any(1)
    T[:,4] = pair; T[:,5] = (wield&weap).any(1)
    T[:,6] = np.minimum(occ.sum(1),30)/30; T[:,7] = np.minimum(food.sum(1),8)/8
    T[:,8] = np.minimum(weap.sum(1),10)/10; T[:,9] = np.minimum(buc1.sum(1),5)/5
    T[:,10] = np.minimum(buc3.sum(1),8)/8
    T[:,11] = np.minimum(np.where(ammo, st[:,:,2],0).sum(1),40)/40
    T[:,12] = np.minimum((buc3&weap).sum(1),4)/4
    T[:,13] = np.minimum((buc1&worn).sum(1),3)/3
    T[:,14] = np.where(spk&occ, spe, -9).max(1).clip(-3,6)/6
    bw = np.where(weap&spk, spe, -9).max(1); M[:,15] = (weap&spk).any(1); T[:,15] = bw.clip(-3,6)/6
    we = np.where(wield&spk, spe, 0).sum(1); M[:,16] = (wield&spk).any(1); T[:,16] = we.clip(-3,6)/6
    er = np.where(worn, st[:,:,3], 9).min(1); M[:,17] = worn.any(1); T[:,17] = np.where(M[:,17]>0, er, 0)/3
    return T, M

def synth_inputs(d):
    N = len(d['gl'])
    occ = d['occ']; st = d['st']
    SF = np.zeros((N,S,12), np.float32)
    SF[:,:,0] = occ
    for c in range(4): SF[:,:,1+c] = st[:,:,0]==c
    spk = st[:,:,1] != -128
    SF[:,:,5] = spk; SF[:,:,6] = np.where(spk, st[:,:,1],0)*0.1
    SF[:,:,7] = np.minimum(st[:,:,2],30)/30
    SF[:,:,8] = st[:,:,3]/3; SF[:,:,9] = 0
    SF[:,:,10] = st[:,:,5]&1; SF[:,:,11] = (st[:,:,5]>>1)&1
    return d['gl'], d['itr'], SF, occ.astype(np.float32), np.clip(d['cls'],0,18)

# ---------------- data ----------------
if REGIME == 'real':
    dtr, dva = load_real()
    Ttr, Mtr, _ = real_targets(dtr); Tva, Mva, _ = real_targets(dva)
    gtr = real_inputs(dtr); gva = real_inputs(dva)
else:
    rng = np.random.default_rng(7)
    dtr = gen_synth(200000, rng, nhi=26)          # size-gen: train caps at 26 items
    dva = gen_synth(60000, np.random.default_rng(8))   # val full range 3..40
    Ttr, Mtr = synth_targets(dtr); Tva, Mva = synth_targets(dva)
    gtr = synth_inputs(dtr); gva = synth_inputs(dva)

Ntr, Nva = len(Ttr), len(Tva)
for k in range(NT):
    if k in BIN: continue
    m = Mtr[:,k] > 0
    mu, sd = Ttr[m,k].mean(), Ttr[m,k].std()+1e-6
    Ttr[:,k] = (Ttr[:,k]-mu)/sd; Tva[:,k] = (Tva[:,k]-mu)/sd

def to_dev(g):
    gl, it, sf, occ, cl = g
    return (torch.tensor(gl,device=dev), torch.tensor(it,device=dev),
            torch.tensor(sf,device=dev,dtype=torch.float32), torch.tensor(occ,device=dev,dtype=torch.float32),
            torch.tensor(cl,device=dev))
Gtr, Gva = to_dev(gtr), to_dev(gva)
Ytr = torch.tensor(Ttr,device=dev); Yva_np = Tva
Mtr_t = torch.tensor(Mtr,device=dev); Mva_np = Mva

# ---------------- zoo ----------------
class Base(nn.Module):
    def __init__(s, W=32):
        super().__init__(); s.W = W
        s.emb = nn.Embedding(GV,24); s.embt = nn.Embedding(GV,8)
        s.l1 = nn.Linear(44,W)
    def slot(s, G, b):
        gl,it,sf,occ,cl = G
        x = torch.cat([s.emb(gl[b]), s.embt(it[b]), sf[b]], -1)
        return torch.relu(s.l1(x))*occ[b].unsqueeze(-1), occ[b], cl[b]
def masked(v, occ, fill): return v.masked_fill(occ.unsqueeze(-1)<.5, fill)

class SumP(Base):
    def __init__(s,W=32,H=64): super().__init__(W); s.l2=nn.Linear(W,H)
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        return torch.relu(s.l2(h)).mul(occ.unsqueeze(-1)).sum(1)*0.2
class MeanP(SumP):
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        return torch.relu(s.l2(h)).mul(occ.unsqueeze(-1)).sum(1)/occ.sum(1,keepdim=True).clamp(1)
class MaxP(Base):
    def __init__(s,W=32): super().__init__(W); s.l2=nn.Linear(W,128)
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        return torch.relu(masked(s.l2(h),occ,-1e9).max(1).values)
class LseP(Base):
    def __init__(s,W=32): super().__init__(W); s.l2=nn.Linear(W,128)
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        return torch.logsumexp(masked(s.l2(h),occ,-1e9),1)
class AttnP(Base):
    def __init__(s,W=32,M=8): super().__init__(W); s.M=M; s.q=nn.Linear(W,M,bias=False)
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        a = torch.softmax(masked(s.q(h),occ,-1e9),1)
        return torch.einsum('bsm,bsk->bmk',a,h).reshape(len(b),-1)
class CountAttn(Base):  # attention + unnormalized score-sum side channel
    def __init__(s,W=32,M=8): super().__init__(W); s.M=M; s.q=nn.Linear(W,M,bias=False)
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        sc = s.q(h)
        a = torch.softmax(masked(sc,occ,-1e9),1)
        att = torch.einsum('bsm,bsk->bmk',a,h).reshape(len(b),-1)
        cnt = (torch.sigmoid(sc)*occ.unsqueeze(-1)).sum(1)*0.2
        return torch.cat([att,cnt],1)
class SelfAttn(Base):
    def __init__(s,W=32): super().__init__(W); s.mha=nn.MultiheadAttention(W,4,batch_first=True); s.q=nn.Linear(W,8,bias=False)
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        msk = occ<.5
        msk = msk.clone(); msk[occ.sum(1)<.5, 0] = False
        h2,_ = s.mha(h,h,h,key_padding_mask=msk)
        h = torch.relu(h+h2)*occ.unsqueeze(-1)
        a = torch.softmax(masked(s.q(h),occ,-1e9),1)
        return torch.einsum('bsm,bsk->bmk',a,h).reshape(len(b),-1)
class PNA(Base):
    def __init__(s,W=32,H=32): super().__init__(W); s.l2=nn.Linear(W,H)
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        v = torch.relu(s.l2(h))*occ.unsqueeze(-1)
        n = occ.sum(1,keepdim=True).clamp(1)
        mean = v.sum(1)/n
        var = (v*v).sum(1)/n - mean*mean
        mx = masked(s.l2(h),occ,-1e9).max(1).values
        return torch.cat([v.sum(1)*0.2, mean, torch.relu(mx), (var.clamp_min(0)+1e-6).sqrt()],1)
class Typed(Base):
    def __init__(s,W=32): super().__init__(W); s.l2=nn.Linear(W,16)
    def forward(s,G,b):
        h,occ,cl = s.slot(G,b)
        oh = nn.functional.one_hot(cl,19).float()*occ.unsqueeze(-1)
        return torch.einsum('bsk,bsc->bck',torch.relu(s.l2(h)),oh[:,:,:13]).reshape(len(b),-1)*0.3
class SortFlat(Base):
    def __init__(s,W=32): super().__init__(W); s.out=nn.Linear(S*W,128)
    def forward(s,G,b):
        h,occ,cl = s.slot(G,b)
        gl = G[0]
        key = (cl*1000+torch.clamp(gl[b],0,999)).float()+(1-occ)*1e6
        idx = key.argsort(1)
        hs = torch.gather(h,1,idx.unsqueeze(-1).expand(-1,-1,s.W))
        return torch.relu(s.out(hs.reshape(len(b),-1)))
class GruP(Base):
    def __init__(s,W=32): super().__init__(W); s.gru=nn.GRU(W,64,batch_first=True)
    def forward(s,G,b):
        h,occ,cl = s.slot(G,b)
        gl = G[0]
        key = (cl*1000+torch.clamp(gl[b],0,999)).float()+(1-occ)*1e6
        idx = key.argsort(1)
        hs = torch.gather(h,1,idx.unsqueeze(-1).expand(-1,-1,s.W))
        return s.gru(hs)[1][0]
class GatedSum(Base):  # production-wld generalized: flag-gated sums + plain
    def __init__(s,W=32): super().__init__(W)
    def forward(s,G,b):
        h,occ,_ = s.slot(G,b)
        sf = G[2][b]
        wld = sf[:,:,11].unsqueeze(-1); wrn = sf[:,:,10].unsqueeze(-1)
        return torch.cat([(h*wld).sum(1),(h*wrn).sum(1),h.sum(1)*0.2],1)
class ProdTriple(nn.Module):  # V5 production topology at W=16
    def __init__(s):
        super().__init__(); s.a=AttnP(16,8); s.s=SumP(16,64); s.g=GatedSum(16)
        s.s.emb=s.a.emb; s.s.embt=s.a.embt; s.s.l1=s.a.l1
        s.g.emb=s.a.emb; s.g.embt=s.a.embt; s.g.l1=s.a.l1
    def forward(s,G,b): return torch.cat([s.a(G,b),s.s(G,b),s.g(G,b)],1)
class SumAttn(nn.Module):
    def __init__(s,W=32):
        super().__init__(); s.a=AttnP(W,8); s.s=SumP(W,64)
        s.s.emb=s.a.emb; s.s.embt=s.a.embt; s.s.l1=s.a.l1
    def forward(s,G,b): return torch.cat([s.a(G,b),s.s(G,b)],1)

class GMPv(Base):  # one generalized pooling block: K heads x (softmax_temp + sigmoid-count)
    def __init__(s,K=8,V=48,W=16):
        super().__init__()
        s.l1 = nn.Linear(44,W)
        s.sc = nn.Linear(W,K,bias=False); s.val = nn.Linear(W,V)
        s.ltau = nn.Parameter(torch.linspace(-0.7,2.1,K))
    def forward(s,G,b):
        gl,it,sf,occ,cl = G
        x = torch.cat([s.emb(gl[b]), s.embt(it[b]), sf[b]],-1)
        r = torch.relu(s.l1(x))*occ[b].unsqueeze(-1)
        v = torch.relu(s.val(r))
        S = s.sc(r); tau = torch.exp(s.ltau)
        A = torch.softmax((S*tau).masked_fill(occ[b].unsqueeze(-1)<.5,-1e9),1)
        att = torch.einsum('bsk,bsd->bkd',A,v).reshape(len(b),-1)
        U = torch.sigmoid(S)*occ[b].unsqueeze(-1)
        cnt = torch.einsum('bsk,bsd->bkd',U,v).reshape(len(b),-1)*0.2
        return torch.cat([att,cnt],1)

BINCOLS=[0,1,2,3,4,5,10,11]
class MinDeep(nn.Module):  # minimal: deep per-entity MLP -> sum|max + predicate gates; keys=r
    def __init__(s,V=64,W=16):
        super().__init__()
        s.emb=nn.Embedding(GV,24); s.embt=nn.Embedding(GV,8)
        s.l1=nn.Linear(44,W); s.v1=nn.Linear(W,64); s.v2=nn.Linear(64,V)
    def forward(s,G,b):
        gl,it,sf,occ,cl=G
        x=torch.cat([s.emb(gl[b]),s.embt(it[b]),sf[b]],-1)
        om=occ[b].unsqueeze(-1)
        r=torch.relu(s.l1(x))*om
        v=torch.relu(s.v2(torch.relu(s.v1(r))))*om
        sm=v.sum(1)*0.2
        mx=torch.relu(v.masked_fill(om<.5,-1e9).max(1).values)
        keys=(sf[b]*om)[:,:,BINCOLS]
        content=torch.cat([r,sf[b]],-1)
        raw=torch.einsum('bsj,bsd->bjd',keys,content)
        gate=(raw/keys.sum(1).clamp(min=1.0)[:,:,None]).reshape(len(b),-1)
        return torch.cat([sm,mx,gate],1)

ZOO = {
 'mindeep': lambda: MinDeep(),
 'gmpv8': lambda: GMPv(8,48),
 'sum32': lambda: SumP(32), 'mean32': lambda: MeanP(32), 'max32': lambda: MaxP(32),
 'lse32': lambda: LseP(32), 'attn1': lambda: AttnP(32,1), 'attn8': lambda: AttnP(32,8),
 'cattn8': lambda: CountAttn(32,8), 'selfattn': lambda: SelfAttn(32), 'pna32': lambda: PNA(32),
 'typed': lambda: Typed(32), 'sortflat': lambda: SortFlat(32), 'gru': lambda: GruP(32),
 'gated32': lambda: GatedSum(32), 'prodtrip': lambda: ProdTriple(),
 'sum8': lambda: SumP(8), 'sum16': lambda: SumP(16), 'sum64': lambda: SumP(64),
 'attn8w16': lambda: AttnP(16,8), 'attn8w64': lambda: AttnP(64,8),
 'cattn8w16': lambda: CountAttn(16,8), 'cattn8w64': lambda: CountAttn(64,8),
 'pna16': lambda: PNA(16), 'pna64': lambda: PNA(64),
 'sumattn32': lambda: SumAttn(32), 'shuffle': lambda: SumP(32),
}

def auc(y,p):
    o=np.argsort(p); rk=np.empty(len(p)); rk[o]=np.arange(1,len(p)+1)
    pos=y>0.5; a,b_=pos.sum(),(~pos).sum()
    if a<25 or b_<25: return float('nan')
    return (rk[pos].sum()-a*(a+1)/2)/(a*b_)

def fit(mk, lr, seed, shuffle=False, epochs=40, BS=2048):
    torch.manual_seed(seed); np.random.seed(seed)
    net = mk().to(dev)
    with torch.no_grad(): Hd = net(Gtr, torch.arange(4,device=dev)).shape[1]
    head = nn.Linear(Hd,NT).to(dev)
    Y = Ytr[torch.tensor(np.random.permutation(Ntr),device=dev)] if shuffle else Ytr
    opt = torch.optim.Adam(list(net.parameters())+list(head.parameters()), lr=lr)
    cut = int(Ntr*0.95)
    for ep in range(epochs):
        perm = torch.tensor(np.random.permutation(cut),device=dev)
        for i in range(0,cut,BS):
            b = perm[i:i+BS]
            p = head(net(Gtr,b))
            loss = (nn.functional.smooth_l1_loss(p,Y[b],reduction='none')*Mtr_t[b]).sum()/Mtr_t[b].sum()
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        tb = torch.arange(cut,Ntr,device=dev)
        tv = (nn.functional.smooth_l1_loss(head(net(Gtr,tb)),Y[tb],reduction='none')*Mtr_t[tb]).sum().item()/Mtr_t[tb].sum().item()
        vi = torch.arange(Nva,device=dev)
        p = torch.cat([head(net(Gva,vi[i:i+BS])) for i in range(0,Nva,BS)]).cpu().numpy()
    res=[]
    for k in range(NT):
        m = Mva_np[:,k]>0
        yv,pv = Yva_np[m,k], p[m,k]
        res.append(float(auc(yv,pv)) if k in BIN else float(1-((yv-pv)**2).sum()/max(((yv-yv.mean())**2).sum(),1e-9)))
    return res, tv, net, head

LRS = [5e-4, 1.5e-3, 4e-3]
with open(OUT,'a') as fo:
    for name, mk in ZOO.items():
        shuf = name=='shuffle'
        for lr in LRS:
            for seed in (0,1,2):
                key = f'{name}|{lr}|{seed}'
                if key in done: continue
                t0=time.time()
                res, tv, net, head = fit(mk, lr, seed, shuffle=shuf)
                rec = {'key':key,'arch':name,'lr':lr,'seed':seed,'trainval':float(tv),'res':res,'t':round(time.time()-t0,1)}
                # duplication diagnostic (synth, sum-family + attn cells): copy item 0 to an empty slot
                fo.write(json.dumps(rec)+'\n'); fo.flush()
                print(key, f'tv={tv:.4f}', f'{time.time()-t0:.0f}s', flush=True)
print('DONE', REGIME)
