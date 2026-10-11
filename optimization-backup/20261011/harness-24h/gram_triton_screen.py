from pathlib import Path
import ctypes,json,time,statistics,hashlib,subprocess
import torch
import triton
import triton.language as tl

@triton.jit
def gram_triangle(X,G,N:tl.constexpr,K:tl.constexpr,B:tl.constexpr,BK:tl.constexpr,TRIANGLE:tl.constexpr):
    mi=tl.program_id(0);ni=tl.program_id(1)
    if not TRIANGLE or mi<=ni:
        m=mi*B+tl.arange(0,B)
        n=ni*B+tl.arange(0,B)
        k=tl.arange(0,BK)
        a=X+m[:,None]+k[None,:]*N
        b=X+k[:,None]*N+n[None,:]
        acc=tl.zeros((B,B),tl.float32)
        for step in range(tl.cdiv(K,BK)):
            av=tl.load(a);bv=tl.load(b)
            acc=tl.dot(av,bv,acc)
            a+=BK*N;b+=BK*N
        out=acc.to(tl.bfloat16)
        tl.store(G+m[:,None]*N+n[None,:],out)
        if TRIANGLE and mi!=ni:
            tl.store(G+n[None,:]*N+m[:,None],out)

def main():
    assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    torch.cuda.set_device(0);torch.manual_seed(713)
    N,K=1024,3072
    x=torch.randn(K,N,device='cuda',dtype=torch.bfloat16)
    out=torch.empty(N,N,device='cuda',dtype=torch.bfloat16)
    lib=ctypes.CDLL(str(Path('gram_reference.so').resolve()))
    lib.gram_init.argtypes=[ctypes.c_void_p];lib.gram_init.restype=None
    lib.gram_run.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int];lib.gram_run.restype=None
    stream=torch.cuda.Stream()
    with torch.cuda.stream(stream):
        lib.gram_init(stream.cuda_stream)
        baseline=lambda:lib.gram_run(x.data_ptr(),out.data_ptr(),N,K)
        baseline();stream.synchronize();ref=out.clone();stream.synchronize()
        configs=[None,(32,32,4,3,True),(64,32,4,3,True),(64,64,4,3,True),(64,64,8,3,True),(64,64,4,5,True),(128,32,4,3,True),(64,64,4,3,False),None]
        rows=[]
        for i,config in enumerate(configs):
            start=time.monotonic()
            if config:
                B,BK,warps,stages,tri=config
                fn=lambda:gram_triangle[(N//B,N//B)](x,out,N,K,B,BK,tri,num_warps=warps,num_stages=stages)
            else:fn=baseline
            fn();stream.synchronize();prep=time.monotonic()-start
            diff=(out.float()-ref.float());rel=(diff.norm()/ref.float().norm()).item();mx=diff.abs().max().item()
            assert torch.isfinite(out).all() and rel<.03,(config,rel,mx)
            graph=torch.cuda.CUDAGraph()
            with torch.cuda.graph(graph,stream=stream):
                for _ in range(64):fn()
            for _ in range(100):graph.replay()
            stream.synchronize()
            times=[]
            for _ in range(5):
                a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
                a.record(stream);graph.replay();b.record(stream);b.synchronize();times.append(a.elapsed_time(b)*1000/64)
            row=dict(index=i,config=config,microseconds=statistics.mean(times),trials=times,prep_seconds=prep,relative_l2=rel,max_abs=mx)
            print(json.dumps(row),flush=True);rows.append(row)
            Path('GRAM_TRITON_SCREEN.rows.json').write_text(json.dumps(rows,indent=2))
            del graph
        base=statistics.mean([rows[0]['microseconds'],rows[-1]['microseconds']])
        for r in rows:r['gain_percent']=100*(base/r['microseconds']-1)
        result=dict(control_us=base,control_drift_percent=100*(rows[-1]['microseconds']/rows[0]['microseconds']-1),rows=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),triton_version=triton.__version__,torch_version=torch.__version__,reference_sha256=hashlib.sha256(Path('gram_reference.so').read_bytes()).hexdigest(),scope='Isolated BF16 GramK3072/N1024. Private4MiB cuBLAS baseline. Compilation and correctness comparisons outside timing. No fulltraining claim.')
        Path('GRAM_TRITON_SCREEN.json').write_text(json.dumps(result,indent=2));print('COMPLETE',base,flush=True)
if __name__=='__main__':main()
