from pathlib import Path
import ctypes,json,time,statistics,hashlib,subprocess
import torch
import triton
import triton.language as tl

@triton.jit
def gram_split(X,P,N:tl.constexpr,K:tl.constexpr,B:tl.constexpr,BK:tl.constexpr,SK:tl.constexpr):
    mi=tl.program_id(0);ni=tl.program_id(1);split=tl.program_id(2)
    if mi<=ni:
        m=mi*B+tl.arange(0,B);n=ni*B+tl.arange(0,B)
        k=split*(K//SK)+tl.arange(0,BK)
        a=X+m[:,None]+k[None,:]*N;b=X+k[:,None]*N+n[None,:]
        acc=tl.zeros((B,B),tl.float32)
        for step in range(K//SK//BK):
            av=tl.load(a);bv=tl.load(b);acc=tl.dot(av,bv,acc);a+=BK*N;b+=BK*N
        tl.store(P+split*N*N+m[:,None]*N+n[None,:],acc)

@triton.jit
def gram_reduce(P,G,N:tl.constexpr,SK:tl.constexpr,BLOCK:tl.constexpr):
    t=tl.program_id(0)*BLOCK+tl.arange(0,BLOCK)
    row=t//N;col=t%N
    pos=tl.minimum(row,col)*N+tl.maximum(row,col)
    total=tl.full((BLOCK,),0,tl.float32)
    for s in range(SK):total+=tl.load(P+s*N*N+pos,t<N*N,0)
    tl.store(G+t,total,t<N*N)

def main():
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    torch.cuda.set_device(0);torch.manual_seed(713)
    N,K=1024,3072;x=torch.randn(K,N,device='cuda',dtype=torch.bfloat16);out=torch.empty(N,N,device='cuda',dtype=torch.bfloat16)
    partials=torch.empty((8,N,N),device='cuda',dtype=torch.float32)
    lib=ctypes.CDLL(str(Path('gram_reference.so').resolve()));lib.gram_init.argtypes=[ctypes.c_void_p];lib.gram_init.restype=None;lib.gram_run.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int];lib.gram_run.restype=None
    stream=torch.cuda.Stream()
    with torch.cuda.stream(stream):
        lib.gram_init(stream.cuda_stream);baseline=lambda:lib.gram_run(x.data_ptr(),out.data_ptr(),N,K)
        baseline();stream.synchronize();ref=out.clone();stream.synchronize()
        configs=[None,(64,32,4,3,2),(64,32,4,3,4),(64,32,4,3,8),(64,64,4,3,4),(32,32,4,3,4),(128,32,4,3,4),None]
        rows=[]
        for i,config in enumerate(configs):
            start=time.monotonic()
            if config:
                B,BK,warps,stages,sk=config
                def fn():
                    gram_split[(N//B,N//B,sk)](x,partials,N,K,B,BK,sk,num_warps=warps,num_stages=stages)
                    gram_reduce[(triton.cdiv(N*N,256),)](partials,out,N,sk,256)
            else:fn=baseline
            fn();stream.synchronize();prep=time.monotonic()-start
            diff=(out.float()-ref.float());rel=(diff.norm()/ref.float().norm()).item();mx=diff.abs().max().item()
            assert torch.isfinite(out).all() and rel<.03,(config,rel,mx)
            graph=torch.cuda.CUDAGraph()
            with torch.cuda.graph(graph,stream=stream):
                for _ in range(64):fn()
            for _ in range(500):graph.replay()
            stream.synchronize();times=[]
            for _ in range(5):
                a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);a.record(stream);graph.replay();b.record(stream);b.synchronize();times.append(a.elapsed_time(b)*1000/64)
            row=dict(index=i,config=config,microseconds=statistics.mean(times),trials=times,prep_seconds=prep,relative_l2=rel,max_abs=mx)
            print(json.dumps(row),flush=True);rows.append(row);Path('GRAM_TRITON_SPLIT.rows.json').write_text(json.dumps(rows,indent=2));del graph
        base=statistics.mean([rows[0]['microseconds'],rows[-1]['microseconds']])
        for r in rows:r['gain_percent']=100*(base/r['microseconds']-1)
        result=dict(control_us=base,control_drift_percent=100*(rows[-1]['microseconds']/rows[0]['microseconds']-1),rows=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Isolated Gram, includes FP32partialreduction+mirror. Not fulltraining.')
        Path('GRAM_TRITON_SPLIT.json').write_text(json.dumps(result,indent=2));print('COMPLETE',base,flush=True)
if __name__=='__main__':main()
