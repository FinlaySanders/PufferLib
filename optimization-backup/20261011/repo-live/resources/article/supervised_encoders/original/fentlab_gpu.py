# Supervised capacity probe (GPU): deep (16->64->64) vs fused (16->W) entity
# blocks under sum|max pooling — 4 tasks + width ladder on the hinge task.
import torch, torch.nn as nn
torch.manual_seed(0)
DEV='cuda'
N=12000; NE=12
dmg=torch.rand(N,NE); quan=torch.randint(1,8,(N,NE)).float()/8
cursed=(torch.rand(N,NE)<0.3).float(); ench=torch.rand(N,NE)*2-1
cls=torch.nn.functional.one_hot(torch.randint(0,4,(N,NE)),4).float()
occ=(torch.rand(N,NE)<0.8).float(); occ[:,0]=1
x=torch.cat([dmg[...,None],quan[...,None],cursed[...,None],ench[...,None],cls],-1)
x=torch.cat([x,torch.randn(N,NE,8)*0.1],-1).to(DEV)
occ=occ.to(DEV)
T={}
T['hinge_max']=(ench*(1-2*cursed)).masked_fill(occ.cpu()<0.5,-9).max(1).values
T['prod_max']=(dmg*quan).masked_fill(occ.cpu()<0.5,-9).max(1).values
T['count_cond']=((cls[...,1]>0.5)&(cursed<0.5)).float().mul(occ.cpu()).sum(1)/NE
T['best_uncursed']=(dmg*(1-cursed)).masked_fill(occ.cpu()<0.5,-9).max(1).values
T={k:v.to(DEV) for k,v in T.items()}

class Block(nn.Module):
    def __init__(s,width,deep):
        super().__init__()
        s.key=nn.Linear(16,16); s.m1=nn.Linear(16,width)
        s.m2=nn.Linear(width,width) if deep else None
        s.head=nn.Linear(2*width,1)
    def forward(s,x,occ):
        k=torch.relu(s.key(x)); v=torch.relu(s.m1(k))
        if s.m2 is not None: v=torch.relu(s.m2(v))
        sm=0.2*(v*occ[...,None]).sum(1)
        mx=v.masked_fill(occ[...,None]<0.5,-1e9).max(1).values.relu()
        return s.head(torch.cat([sm,mx],-1)).squeeze(-1)

def fit(width,deep,y,epochs=600):
    m=Block(width,deep).to(DEV); opt=torch.optim.Adam(m.parameters(),3e-3)
    tr=slice(0,10000); te=slice(10000,N)
    for ep in range(epochs):
        opt.zero_grad(); p=m(x[tr],occ[tr]); ((p-y[tr])**2).mean().backward(); opt.step()
    with torch.no_grad():
        p=m(x[te],occ[te]); return float(1-((p-y[te])**2).mean()/y[te].var())

print('=== 4 tasks: deep-64 vs fused-64 vs fused-128 ===')
print('%-14s %8s %9s %9s'%('task','deep64','fused64','fused128'))
for name,y in T.items():
    print('%-14s %8.3f %9.3f %9.3f'%(name,fit(64,True,y),fit(64,False,y),fit(128,False,y)))
print('=== hinge width ladder (fused) ===')
for w in (64,128,256,512):
    print('fused-%-4d hinge R2 %.3f'%(w,fit(w,False,T['hinge_max'])))
print('deep-64    hinge R2 %.3f'%fit(64,True,T['hinge_max']))
