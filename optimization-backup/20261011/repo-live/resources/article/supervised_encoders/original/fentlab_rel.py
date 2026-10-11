# Cross-entity relational probe: does the pooled path carry "kit contains a
# launcher AND matching ammo"? Targets require conjoining two entities'
# identities through sum|max pooling (conjunction forms downstream: 1 hidden
# layer on the head, mirroring trunk depth).
import torch, torch.nn as nn
torch.manual_seed(0)
N=12000; NE=12
# entity identity: class one-hot 6 = [bow, crossbow, arrow, bolt, sword, junk]
ident=torch.randint(0,6,(N,NE))
cls=torch.nn.functional.one_hot(ident,6).float()
occ=(torch.rand(N,NE)<0.75).float(); occ[:,0]=1
x=torch.cat([cls,torch.rand(N,NE,4),torch.randn(N,NE,6)*0.1],-1)  # 16-d
has=lambda c:((ident==c).float()*occ).amax(1)
# matched pair: (bow & arrow) or (crossbow & bolt); mismatched decoy pairs abound
y_match=((has(0)*has(2)) + (has(1)*has(3))).clamp(max=1)
y_count=(((ident==2)|(ident==3)).float()*occ).sum(1)/NE  # ammo census control
class Block(nn.Module):
    def __init__(s,width,deep):
        super().__init__()
        s.key=nn.Linear(16,16); s.m1=nn.Linear(16,width)
        s.m2=nn.Linear(width,width) if deep else None
        s.h1=nn.Linear(2*width,64); s.h2=nn.Linear(64,1)  # 1-hidden head = trunk analog
    def forward(s,x,occ):
        k=torch.relu(s.key(x)); v=torch.relu(s.m1(k))
        if s.m2 is not None: v=torch.relu(s.m2(v))
        sm=0.2*(v*occ[...,None]).sum(1)
        mx=v.masked_fill(occ[...,None]<0.5,-1e9).max(1).values.relu()
        return s.h2(torch.relu(s.h1(torch.cat([sm,mx],-1)))).squeeze(-1)
def fit(width,deep,y):
    m=Block(width,deep); opt=torch.optim.Adam(m.parameters(),3e-3)
    tr=slice(0,10000); te=slice(10000,N)
    for ep in range(600):
        opt.zero_grad(); p=m(x[tr],occ[tr]); ((p-y[tr])**2).mean().backward(); opt.step()
    with torch.no_grad():
        p=m(x[te],occ[te]); return float(1-((p-y[te])**2).mean()/y[te].var())
for name,y in [('launcher-ammo match',y_match),('ammo census',y_count)]:
    print('%-20s deep64 %.3f | fused64 %.3f | fused128 %.3f'%(
        name,fit(64,True,y),fit(64,False,y),fit(128,False,y)))
