import triton
import triton.language as tl

@triton.jit
def entity_train_fused(X,W1,B1,W2,B2,GID,C,AMAX,H1,V,
                 N:tl.constexpr,R:tl.constexpr,PAD:tl.constexpr,
                 OFF:tl.constexpr,EPS:tl.constexpr):
    b=tl.program_id(0)
    r=tl.arange(0,R)
    k=tl.arange(0,16)
    d=tl.arange(0,64)
    x=tl.load(X+(b*N+r[:,None])*16+k[None,:],r[:,None]<N,other=0)
    w1=tl.load(W1+d[None,:]*16+k[:,None])
    bias1=tl.load(B1+d)
    h=tl.maximum(tl.dot(x,w1).to(tl.bfloat16).to(tl.float32)+bias1[None,:],0.).to(tl.bfloat16)
    w2=tl.load(W2+d[None,:]*64+d[:,None])
    bias2=tl.load(B2+d)
    v=tl.maximum(tl.dot(h,w2).to(tl.bfloat16).to(tl.float32)+bias2[None,:],0.).to(tl.bfloat16)
    tl.store(H1+(b*N+r[:,None])*64+d[None,:],h,r[:,None]<N)
    tl.store(V+(b*N+r[:,None])*64+d[None,:],v,r[:,None]<N)
    gid=tl.load(GID+b*N+r,r<N,other=PAD)
    if PAD>=0:
        valid=(r<N)&(gid!=PAD)
    else:
        valid=(r<N)&(gid>=0.)
    vf=v.to(tl.float32)
    sm=tl.sum(tl.where(valid[:,None],vf,0.),axis=0)
    mx=tl.max(tl.where(valid[:,None],vf,-1.e30),axis=0)
    arg=tl.min(tl.where(valid[:,None]&(vf==mx[None,:]),r[:,None],2147483647),axis=0)
    found=arg!=2147483647
    tl.store(AMAX+b*64+d,tl.where(found,arg,-1).to(tl.float32))
    tl.store(C+b*1698+OFF+d,(sm*EPS).to(tl.bfloat16))
    tl.store(C+b*1698+OFF+64+d,tl.where(found,mx,0.).to(tl.bfloat16))
