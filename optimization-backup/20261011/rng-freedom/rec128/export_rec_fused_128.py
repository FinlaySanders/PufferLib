# Screen Triton tilings of recurrent_fused at M=128 against the cuBLAS GEMM + gate reference, export the best cubin,
# and emit rec_fused.cuh with both the original M=512 kernel and the new M=128 one.
import sys, ctypes, json, statistics, subprocess, hashlib, time
from pathlib import Path
sys.path.insert(0,'/puffertank/experiments/nethack-24h-20261009')
import torch, triton
from rec_fused_screen import recurrent_fused
H24=Path('/puffertank/experiments/nethack-24h-20261009'); OUT=Path(__file__).resolve().parent
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
torch.cuda.set_device(0); torch.manual_seed(981)
m,h=128,1024
x=torch.randn(m,h,device='cuda',dtype=torch.bfloat16); w=(torch.randn(3*h,h,device='cuda')/h**.5).to(torch.bfloat16)
state=torch.randn(m,h,device='cuda',dtype=torch.bfloat16); combined=torch.empty(m,3*h,device='cuda',dtype=torch.bfloat16)
out=torch.empty_like(x); ns=torch.empty_like(x)
lib=ctypes.CDLL(str(H24/'rec_fused_reference.so')); lib.rec_init.argtypes=[ctypes.c_void_p]; lib.rec_init.restype=None
lib.rec_run.argtypes=[ctypes.c_void_p]*6+[ctypes.c_int]*2; lib.rec_run.restype=None
stream=torch.cuda.Stream(); torch.cuda.synchronize()
configs=[None,(32,32,32,4,3),(32,32,64,4,3),(32,64,32,4,3),(64,32,32,4,3),(64,32,64,4,3),(16,32,32,4,3),(32,32,32,2,3),(32,64,64,4,4),None]
rows=[]
with torch.cuda.stream(stream):
    lib.rec_init(stream.cuda_stream)
    base=lambda: lib.rec_run(x.data_ptr(),w.data_ptr(),combined.data_ptr(),state.data_ptr(),out.data_ptr(),ns.data_ptr(),m,h)
    base(); stream.synchronize(); ref_out=out.clone(); ref_ns=ns.clone()
    for config in configs:
        if config:
            bm,bn,bk,warps,stages=config
            fn=lambda: recurrent_fused[(m//bm,h//bn)](x,w,state,out,ns,m,h,bm,bn,bk,num_warps=warps,num_stages=stages)
        else: fn=base
        fn(); stream.synchronize(); proof={}
        for name,actual,ref in [('out',out,ref_out),('state',ns,ref_ns)]:
            df=actual.float()-ref.float(); proof[name]={'rel_l2':(df.norm()/ref.float().norm()).item(),'max_abs':df.abs().max().item(),'different':int((actual!=ref).sum())}
            assert torch.isfinite(actual).all() and proof[name]['rel_l2']<.03,(config,proof)
        g=torch.cuda.CUDAGraph()
        with torch.cuda.graph(g,stream=stream):
            for _ in range(64): fn()
        for _ in range(100): g.replay()
        stream.synchronize(); ts=[]
        for _ in range(5):
            a=torch.cuda.Event(enable_timing=True); b=torch.cuda.Event(enable_timing=True); a.record(stream); g.replay(); b.record(stream); b.synchronize(); ts.append(a.elapsed_time(b)*1000/64)
        rows.append(dict(config=config,us=statistics.mean(ts),proof=proof)); print(json.dumps(rows[-1]),flush=True); del g
control=statistics.mean([rows[0]['us'],rows[-1]['us']]); best=min((r for r in rows if r['config']),key=lambda r:r['us'])
print(f"CONTROL cublas+gate {control:.1f} us; BEST {best['config']} {best['us']:.1f} us ({100*(control/best['us']-1):+.1f}%)")
bm,bn,bk,warps,stages=best['config']
k=recurrent_fused.warmup(x,w,state,out,ns,m,h,bm,bn,bk,grid=(m//bm,h//bn),num_warps=warps,num_stages=stages)
meta=k.metadata._asdict(); assert meta['global_scratch_size']==0 and meta['profile_scratch_size']==0
cub128=k.asm['cubin']; (OUT/'rec_fused_128x1024.cubin').write_bytes(cub128)
cub512=(H24/'rec_fused_512x1024.cubin').read_bytes(); meta512=json.load(open(H24/'REC_FUSED_EXPORT.json'))['metadata']
arr=lambda data: '\n'.join(','.join(str(b) for b in data[i:i+24])+',' for i in range(0,len(data),24))
hdr=f'''#include <cuda.h>
// Fused recurrent GEMM+gate (Triton, SM89): M=512 prototype (grid 8x32, BM64 BN32 BK32) and M=128 ({bm},{bn},{bk}, {warps} warps, {stages} stages).
// Projected values round to BF16 before gates, as the unfused path does.
static const unsigned char rec_fused_cubin[] = {{
{arr(cub512)}
}};
static const unsigned char rec_fused_cubin_128[] = {{
{arr(cub128)}
}};
thread_local CUmodule g_rec_fused_module = NULL, g_rec_fused_module_128 = NULL;
thread_local CUfunction g_rec_fused_function = NULL, g_rec_fused_function_128 = NULL;
static void rec_fused_init() {{
    if (!getenv("PUF_FUSED_RECURRENT") || !atoi(getenv("PUF_FUSED_RECURRENT"))) return;
    if (g_rec_fused_function) return;
    int device; cudaDeviceProp properties;
    assert(cudaGetDevice(&device) == cudaSuccess);
    assert(cudaGetDeviceProperties(&properties, device) == cudaSuccess);
    assert(properties.major == 8 && properties.minor == 9);
    assert(cuModuleLoadData(&g_rec_fused_module, rec_fused_cubin) == CUDA_SUCCESS);
    assert(cuModuleGetFunction(&g_rec_fused_function, g_rec_fused_module, "{meta512['name']}") == CUDA_SUCCESS);
    assert(cuModuleLoadData(&g_rec_fused_module_128, rec_fused_cubin_128) == CUDA_SUCCESS);
    assert(cuModuleGetFunction(&g_rec_fused_function_128, g_rec_fused_module_128, "{meta['name']}") == CUDA_SUCCESS);
    fprintf(stderr, "REC_FUSED_READY M512 shared={meta512['shared']} M128 shared={meta['shared']} grid={m//bm}x{h//bn}\\n");
}}
static bool rec_fused_try(void* x, void* w, void* state, void* out,
        int B, int H, cudaStream_t stream) {{
    if (!g_rec_fused_function || H != 1024 || (B != 512 && B != 128)) return false;
    assert(x != out);
    void* scratch = NULL;
    void* parameters[] = {{&x, &w, &state, &out, &state, &scratch, &scratch}};
    if (B == 512)
        assert(cuLaunchKernel(g_rec_fused_function, 8, 32, 1, 128, 1, 1, {meta512['shared']}, stream, parameters, NULL) == CUDA_SUCCESS);
    else
        assert(cuLaunchKernel(g_rec_fused_function_128, {m//bm}, {h//bn}, 1, {32*warps}, 1, 1, {meta['shared']}, stream, parameters, NULL) == CUDA_SUCCESS);
    return true;
}}
'''
(OUT/'rec_fused.cuh.generated').write_text(hdr)
json.dump(dict(best=best,control_us=control,rows=rows,meta128={k2:str(v) for k2,v in meta.items()},cubin128_sha256=hashlib.sha256(cub128).hexdigest()),open(OUT/'REC128_SCREEN.json','w'),indent=1,default=str)
print('EXPORT_DONE', meta['name'], meta['shared'], len(cub128))
