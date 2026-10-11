import torch, torch.nn as nn
torch.manual_seed(0)
E=16; N=12000; NE=12
dmg=torch.rand(N,NE); quan=torch.randint(1,8,(N,NE)).float()/8
cursed=(torch.rand(N,NE)<0.3).float(); ench=torch.rand(N,NE)*2-1
cls=torch.nn.functional.one_hot(torch.randint(0,4,(N,NE)),4).float()
occ=(torch.rand(N,NE)<0.8).float(); occ[:,0]=1
x=torch.cat([dmg[...,None],quan[...,None],cursed[...,None],ench[...,None],cls],-1)
x=torch.cat([x,torch.randn(N,NE,8)*0.1],-1)
y=(ench*(1-2*cursed)).masked_fill(occ<0.5,-9).max(1).values
class Block(nn.Module):
    def __init__(s,width,deep=False):
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
tr=slice(0,10000); te=slice(10000,N)
for label,width,deep in [('fused-64',64,False),('fused-128',128,False),('fused-256',256,False),('deep-64',64,True)]:
    m=Block(width,deep); opt=torch.optim.Adam(m.parameters(),3e-3)
    for ep in range(400):
        opt.zero_grad(); p=m(x[tr],occ[tr]); ((p-y[tr])**2).mean().backward(); opt.step()
    with torch.no_grad():
        p=m(x[te],occ[te]); r2=1-((p-y[te])**2).mean()/y[te].var()
    print('%-10s hinge R2 %.3f'%(label,r2))
