# Supervised capacity test: deep (16->64->64) vs fused (16->64) entity value
# blocks under sum|max pooling, on the klab-style sharpened tasks.
import torch, torch.nn as nn, math
torch.manual_seed(0)
DEV='cpu'; E=16; N=12000; NE=12  # entities per set

def make_sets():
    # per-entity latent attributes: dmg, quan, cursed, ench, cls (one-hot 4)
    dmg=torch.rand(N,NE); quan=torch.randint(1,8,(N,NE)).float()/8
    cursed=(torch.rand(N,NE)<0.3).float(); ench=torch.rand(N,NE)*2-1
    cls=torch.nn.functional.one_hot(torch.randint(0,4,(N,NE)),4).float()
    occ=(torch.rand(N,NE)<0.8).float(); occ[:,0]=1
    x=torch.cat([dmg[...,None],quan[...,None],cursed[...,None],ench[...,None],cls],-1) # 8 raw
    x=torch.cat([x,torch.randn(N,NE,8)*0.1],-1)  # pad to 16 with noise dims
    return x,occ,dmg,quan,cursed,ench,cls

x,occ,dmg,quan,cursed,ench,cls=make_sets()
# tasks (set-level targets):
T={}
T['hinge_max']   =(ench*(1-2*cursed)).masked_fill(occ<0.5,-9).max(1).values          # sign-flip hinge, max
T['prod_max']    =(dmg*quan).masked_fill(occ<0.5,-9).max(1).values                    # product, max
T['count_cond']  =((cls[...,1]>0.5)&(cursed<0.5)).float().mul(occ).sum(1)/NE          # conditional count, sum
T['best_uncursed']=(dmg*(1-cursed)).masked_fill(occ<0.5,-9).max(1).values             # gate*value, max

class Block(nn.Module):
    def __init__(s,deep):
        super().__init__()
        s.key=nn.Linear(16,16); s.m1=nn.Linear(16,64)
        s.m2=nn.Linear(64,64) if deep else None
        s.head=nn.Linear(128,1)
    def forward(s,x,occ):
        k=torch.relu(s.key(x)); v=torch.relu(s.m1(k))
        if s.m2 is not None: v=torch.relu(s.m2(v))
        sm=0.2*(v*occ[...,None]).sum(1)
        mx=v.masked_fill(occ[...,None]<0.5,-1e9).max(1).values.relu()
        return s.head(torch.cat([sm,mx],-1)).squeeze(-1)

tr=slice(0,10000); te=slice(10000,N)
print('%-14s %8s %8s'%('task','deep R2','fused R2'))
for name,y in T.items():
    r2s=[]
    for deep in (True,False):
        m=Block(deep); opt=torch.optim.Adam(m.parameters(),3e-3)
        for ep in range(400):
            opt.zero_grad(); p=m(x[tr],occ[tr]); loss=((p-y[tr])**2).mean(); loss.backward(); opt.step()
        with torch.no_grad():
            p=m(x[te],occ[te]); ss=((p-y[te])**2).mean(); var=y[te].var()
            r2s.append(1-ss/var)
    print('%-14s %8.3f %8.3f'%(name,r2s[0],r2s[1]))
