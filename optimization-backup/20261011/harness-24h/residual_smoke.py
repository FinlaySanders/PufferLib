from pathlib import Path
import torch,ctypes,json,hashlib,subprocess

assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
torch.manual_seed(191);torch.cuda.set_device(0)
lib=ctypes.CDLL(str(Path('residual_reference.so').resolve()))
lib.rec_init.argtypes=[ctypes.c_void_p];lib.rec_init.restype=None
lib.residual_run.argtypes=[ctypes.c_void_p]*4+[ctypes.c_int]*3;lib.residual_run.restype=None
stream=torch.cuda.Stream();lib.rec_init(stream.cuda_stream)
rows=[]
with torch.cuda.stream(stream):
    for m,h in [(1,7),(17,32),(128,512),(4096,1024)]:
        for mode in ['dense','sparse','zero']:
            x=torch.randn(m,3*h,device='cuda',dtype=torch.bfloat16)*.01
            w=(torch.randn(3*h,h,device='cuda')/h**.5).to(torch.bfloat16)
            residual=torch.randn(m,h,device='cuda',dtype=torch.bfloat16)*.01
            if mode=='sparse':x*=torch.rand_like(x)>.95
            if mode=='zero':x.zero_();residual.zero_()
            a=torch.empty_like(residual);b=torch.empty_like(a)
            lib.residual_run(x.data_ptr(),w.data_ptr(),residual.data_ptr(),a.data_ptr(),m,h,0)
            lib.residual_run(x.data_ptr(),w.data_ptr(),residual.data_ptr(),b.data_ptr(),m,h,1)
            stream.synchronize()
            d=b.float()-a.float();norm=a.float().norm().item()
            relative=d.norm().item()/norm if norm else d.norm().item()
            row=dict(m=m,h=h,mode=mode,relative_l2=relative,max_abs=d.abs().max().item(),different=(a!=b).sum().item(),elements=a.numel())
            assert torch.isfinite(a).all() and torch.isfinite(b).all() and relative<.01,row
            rows.append(row);print(json.dumps(row),flush=True)
result=dict(cases=len(rows),elements=sum(r['elements'] for r in rows),maximum_relative_l2=max(r['relative_l2'] for r in rows),rows=rows,reference_sha256=hashlib.sha256(Path('residual_reference.so').read_bytes()).hexdigest(),scope='Basic GEMM residual scale/layout smoke. BF16 intermediate rounding differs. Not an actual optimizer-state or long-term stability check. Copy before beta1 only initializes synthetic residual; no timing claim.')
Path('RESIDUAL_GEMM_SMOKE.json').write_text(json.dumps(result,indent=2))
