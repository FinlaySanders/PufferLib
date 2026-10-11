from pathlib import Path
import ctypes, json, statistics, subprocess, hashlib, time
import torch
import triton
import triton.language as tl

@triton.jit
def stable_sigmoid(x):
    z=tl.exp(-tl.abs(x))
    return tl.where(x>=0,1./(1.+z),z/(1.+z))

@triton.jit
def recurrent_fused(X,W,S,Y,NS,M:tl.constexpr,H:tl.constexpr,
                    BM:tl.constexpr,BN:tl.constexpr,BK:tl.constexpr):
    mi=tl.program_id(0);ni=tl.program_id(1)
    m=mi*BM+tl.arange(0,BM)
    n=ni*BN+tl.arange(0,BN)
    k=tl.arange(0,BK)
    xp=X+m[:,None]*H+k[None,:]
    wp=W+n[None,:]*H+k[:,None]
    hacc=tl.zeros((BM,BN),tl.float32)
    zacc=tl.zeros((BM,BN),tl.float32)
    sacc=tl.zeros((BM,BN),tl.float32)
    for step in range(tl.cdiv(H,BK)):
        xv=tl.load(xp)
        wh=tl.load(wp)
        wz=tl.load(wp+H*H)
        ws=tl.load(wp+2*H*H)
        hacc=tl.dot(xv,wh,hacc)
        zacc=tl.dot(xv,wz,zacc)
        sacc=tl.dot(xv,ws,sacc)
        xp+=BK;wp+=BK
    hidden=hacc.to(tl.bfloat16).to(tl.float32)
    gate=zacc.to(tl.bfloat16).to(tl.float32)
    proj=sacc.to(tl.bfloat16).to(tl.float32)
    state=tl.load(S+m[:,None]*H+n[None,:]).to(tl.float32)
    x=tl.load(X+m[:,None]*H+n[None,:]).to(tl.float32)
    z=stable_sigmoid(gate)
    ht=tl.where(hidden>=0,hidden+0.5,stable_sigmoid(hidden))
    diff=ht-state
    hout=tl.where(tl.abs(z)<0.5,state+z*diff,ht-diff*(1.-z))
    s=stable_sigmoid(proj)
    y=s*hout+(1.-s)*x
    tl.store(NS+m[:,None]*H+n[None,:],hout.to(tl.bfloat16))
    tl.store(Y+m[:,None]*H+n[None,:],y.to(tl.bfloat16))

def main():
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    torch.cuda.set_device(0);torch.manual_seed(981)
    m,h=512,1024
    x=torch.randn(m,h,device='cuda',dtype=torch.bfloat16)
    w=(torch.randn(3*h,h,device='cuda')/h**.5).to(torch.bfloat16)
    state=torch.randn(m,h,device='cuda',dtype=torch.bfloat16)
    combined=torch.empty(m,3*h,device='cuda',dtype=torch.bfloat16)
    out=torch.empty_like(x);ns=torch.empty_like(x)
    lib=ctypes.CDLL(str(Path('rec_fused_reference.so').resolve()))
    lib.rec_init.argtypes=[ctypes.c_void_p];lib.rec_init.restype=None
    lib.rec_run.argtypes=[ctypes.c_void_p]*6+[ctypes.c_int]*2;lib.rec_run.restype=None
    stream=torch.cuda.Stream();torch.cuda.synchronize()
    rows=[]
    configs=[None,(32,32,32,4,3),(32,32,64,4,3),(32,64,32,4,3),(32,64,64,4,3),
             (64,32,32,4,3),(64,32,64,4,3),(64,64,32,4,3),(64,64,64,8,3),
             (32,64,64,4,4),(64,32,64,4,4),None]
    with torch.cuda.stream(stream):
        lib.rec_init(stream.cuda_stream)
        base=lambda:lib.rec_run(x.data_ptr(),w.data_ptr(),combined.data_ptr(),state.data_ptr(),out.data_ptr(),ns.data_ptr(),m,h)
        base();stream.synchronize();ref_out=out.clone();ref_ns=ns.clone();stream.synchronize()
        for index,config in enumerate(configs):
            t=time.monotonic()
            if config:
                bm,bn,bk,warps,stages=config
                fn=lambda:recurrent_fused[(m//bm,h//bn)](x,w,state,out,ns,m,h,bm,bn,bk,num_warps=warps,num_stages=stages)
            else:fn=base
            fn();stream.synchronize();prep=time.monotonic()-t
            proof={}
            for name,actual,reference in [('out',out,ref_out),('state',ns,ref_ns)]:
                df=actual.float()-reference.float()
                proof[name]={'relative_l2':(df.norm()/reference.float().norm()).item(),'max_abs':df.abs().max().item(),'different':(actual!=reference).sum().item()}
                assert torch.isfinite(actual).all() and proof[name]['relative_l2']<.03,(config,name,proof)
            g=torch.cuda.CUDAGraph()
            with torch.cuda.graph(g,stream=stream):
                for _ in range(64):fn()
            for _ in range(200):g.replay()
            stream.synchronize()
            ts=[]
            for _ in range(5):
                a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
                a.record(stream);g.replay();b.record(stream);b.synchronize();ts.append(a.elapsed_time(b)*1000/64)
            row=dict(index=index,config=config,microseconds=statistics.mean(ts),trials=ts,proof=proof,prep_seconds=prep)
            print(json.dumps(row),flush=True);rows.append(row)
            Path('REC_FUSED_SCREEN.rows.json').write_text(json.dumps(rows,indent=2))
            del g
    control=statistics.mean([rows[0]['microseconds'],rows[-1]['microseconds']])
    for r in rows:r['gain_percent']=100*(control/r['microseconds']-1)
    result=dict(control_us=control,control_drift_percent=100*(rows[-1]['microseconds']/rows[0]['microseconds']-1),rows=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(Path('rec_fused_reference.so').read_bytes()).hexdigest(),triton_version=triton.__version__,scope='One inference layer, M512 H1024, BF16 projected-value rounding retained. cuBLAS private4MiB + exact extracted gate baseline. All movement included, no in-place input/output alias.')
    Path('REC_FUSED_SCREEN.json').write_text(json.dumps(result,indent=2));print('COMPLETE',control,flush=True)

if __name__=='__main__':main()
