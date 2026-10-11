from pathlib import Path
import ctypes,json,time,statistics,hashlib,subprocess
import torch,triton
import triton.language as tl

@triton.jit
def inventory_fused(X,W1,B1,W2,B2,GID,C,AMAX,H1,V,
                    SAVE:tl.constexpr,SEQUENTIAL:tl.constexpr):
    b=tl.program_id(0)
    r=tl.arange(0,64)
    k=tl.arange(0,16)
    d=tl.arange(0,64)
    x=tl.load(X+(b*55+r[:,None])*16+k[None,:],r[:,None]<55,other=0)
    w1=tl.load(W1+d[None,:]*16+k[:,None])
    a=tl.dot(x,w1)
    bias1=tl.load(B1+d)
    h=tl.maximum(a+bias1[None,:],0.).to(tl.bfloat16)
    w2=tl.load(W2+d[None,:]*64+r[:,None])
    z=tl.dot(h,w2)
    bias2=tl.load(B2+d)
    v=tl.maximum(z+bias2[None,:],0.).to(tl.bfloat16)
    if SAVE:
        tl.store(H1+(b*55+r[:,None])*64+d[None,:],h,r[:,None]<55)
        tl.store(V+(b*55+r[:,None])*64+d[None,:],v,r[:,None]<55)
    gid=tl.load(GID+b*55+r,r<55,other=5976)
    valid=(r<55)&(gid!=5976.)
    vf=v.to(tl.float32)
    sm=tl.sum(tl.where(valid[:,None],vf,0.),axis=0)
    mx=tl.max(tl.where(valid[:,None],vf,-1.e30),axis=0)
    arg=tl.min(tl.where(valid[:,None]&(vf==mx[None,:]),r[:,None],2147483647),axis=0)
    found=arg!=2147483647
    tl.store(AMAX+b*64+d,tl.where(found,arg,-1).to(tl.float32))
    tl.store(C+b*1698+1010+d,(sm*.2).to(tl.bfloat16))
    tl.store(C+b*1698+1074+d,tl.where(found,mx,0.).to(tl.bfloat16))

def main():
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    torch.cuda.set_device(0);torch.manual_seed(345)
    batch=512
    x=torch.rand(batch,55,16,device='cuda',dtype=torch.bfloat16)
    w1=(torch.randn(64,16,device='cuda')*.1).to(torch.bfloat16)
    w2=(torch.randn(64,64,device='cuda')*.1).to(torch.bfloat16)
    b1=(torch.randn(64,device='cuda')*.1).to(torch.bfloat16)
    b2=(torch.randn(64,device='cuda')*.1).to(torch.bfloat16)
    gid=torch.randint(0,5976,(batch,55),device='cuda').float()
    gid[torch.rand_like(gid)>.5]=5976
    gid[0]=5976
    h=torch.empty(batch,55,64,device='cuda',dtype=torch.bfloat16);v=torch.empty_like(h)
    c=torch.full((batch,1698),-64,device='cuda',dtype=torch.bfloat16)
    amax=torch.empty(batch,64,device='cuda')
    lib=ctypes.CDLL(str(Path('inventory_fused_reference.so').resolve()))
    lib.inv_init.argtypes=[ctypes.c_void_p]*3+[ctypes.c_int];lib.inv_init.restype=None
    lib.inv_run.argtypes=[ctypes.c_void_p]*8+[ctypes.c_int];lib.inv_run.restype=None
    stream=torch.cuda.Stream();torch.cuda.synchronize();rows=[]
    with torch.cuda.stream(stream):
        lib.inv_init(stream.cuda_stream,b1.data_ptr(),b2.data_ptr(),batch)
        baseline=lambda:lib.inv_run(x.data_ptr(),w1.data_ptr(),w2.data_ptr(),h.data_ptr(),v.data_ptr(),gid.data_ptr(),c.data_ptr(),amax.data_ptr(),batch)
        baseline();stream.synchronize()
        ref=c.clone();ref_amax=amax.clone();stream.synchronize()
        for index,config in enumerate([None,(4,1,False),(4,2,False),(8,1,False),(4,1,True),(8,2,False),None]):
            t=time.monotonic()
            if config:
                warps,stages,save=config
                fn=lambda:inventory_fused[(batch,)](x,w1,b1,w2,b2,gid,c,amax,h,v,save,False,num_warps=warps,num_stages=stages)
            else:fn=baseline
            fn();stream.synchronize()
            prep=time.monotonic()-t
            ca=c[:,1010:1138].float();ra=ref[:,1010:1138].float();diff=ca-ra
            proof=dict(relative_l2=(diff.norm()/ra.norm()).item(),max_abs=diff.abs().max().item(),argmax_different=(amax!=ref_amax).sum().item(),finite=bool(torch.isfinite(c).all()),untouched=bool((c[:,:1010]==-64).all() and (c[:,1138:]==-64).all()))
            assert proof['finite'] and proof['untouched'] and proof['relative_l2']<.03,(config,proof)
            g=torch.cuda.CUDAGraph()
            with torch.cuda.graph(g,stream=stream):
                for _ in range(64):fn()
            for _ in range(200):g.replay()
            stream.synchronize();ts=[]
            for _ in range(5):
                a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
                a.record(stream);g.replay();b.record(stream);b.synchronize();ts.append(a.elapsed_time(b)*1000/64)
            row=dict(index=index,config=config,microseconds=statistics.mean(ts),trials=ts,proof=proof,prep_seconds=prep)
            rows.append(row);print(json.dumps(row),flush=True)
            Path('INVENTORY_FUSED_SCREEN.rows.json').write_text(json.dumps(rows,indent=2));del g
    control=statistics.mean([rows[0]['microseconds'],rows[-1]['microseconds']])
    for r in rows:r['gain_percent']=100*(control/r['microseconds']-1)
    result=dict(control_us=control,control_drift_percent=100*(rows[-1]['microseconds']/rows[0]['microseconds']-1),rows=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(Path('inventory_fused_reference.so').read_bytes()).hexdigest(),scope='Inventory 16->64->64 bias/ReLU plus masked sum/max; 512 games,55slots. Baseline uses current inference cuBLASLt fused bias/ReLU and exact extracted pool. Pointer keys untouched. Synthetic inputs; reduction/order differences quantified. No training claim.')
    Path('INVENTORY_FUSED_SCREEN.json').write_text(json.dumps(result,indent=2));print('COMPLETE',control,flush=True)

if __name__=='__main__':main()
