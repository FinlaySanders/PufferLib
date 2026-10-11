from pathlib import Path
import json,hashlib,subprocess
import torch
from rec_fused_screen import recurrent_fused

assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
root=Path(__file__).resolve().parent
x=torch.empty(512,1024,device='cuda',dtype=torch.bfloat16)
w=torch.empty(3072,1024,device='cuda',dtype=torch.bfloat16)
s=torch.empty_like(x);out=torch.empty_like(x);ns=torch.empty_like(x)
k=recurrent_fused.warmup(x,w,s,out,ns,512,1024,64,32,32,grid=(8,32),num_warps=4,num_stages=3)
(root/'rec_fused_512x1024.cubin').write_bytes(k.asm['cubin'])
(root/'rec_fused_512x1024.ptx').write_text(k.asm['ptx'])
meta=k.metadata._asdict()
assert meta['global_scratch_size']==0 and meta['profile_scratch_size']==0
(root/'REC_FUSED_EXPORT.json').write_text(json.dumps({'metadata':meta,'cubin_sha256':hashlib.sha256(k.asm['cubin']).hexdigest(),'source_sha256':hashlib.sha256((root/'rec_fused_screen.py').read_bytes()).hexdigest()},indent=2,default=str))
data=k.asm['cubin']
array='\n'.join(','.join(str(x) for x in data[i:i+24])+',' for i in range(0,len(data),24))
header='''#include <cuda.h>
// Isolated SM89/M512/H1024 prototype. Projected values round to BF16 before gates.
static const unsigned char rec_fused_cubin[] = {
'''+array+'''
};
thread_local CUmodule g_rec_fused_module = NULL;
thread_local CUfunction g_rec_fused_function = NULL;
static void rec_fused_init() {
    if (!getenv("PUF_FUSED_RECURRENT") || !atoi(getenv("PUF_FUSED_RECURRENT"))) return;
    if (g_rec_fused_function) return;
    int device;
    cudaDeviceProp properties;
    assert(cudaGetDevice(&device) == cudaSuccess);
    assert(cudaGetDeviceProperties(&properties, device) == cudaSuccess);
    assert(properties.major == 8 && properties.minor == 9);
    assert(cuModuleLoadData(&g_rec_fused_module, rec_fused_cubin) == CUDA_SUCCESS);
    assert(cuModuleGetFunction(&g_rec_fused_function, g_rec_fused_module, "'''+meta['name']+'''") == CUDA_SUCCESS);
    fprintf(stderr, "REC_FUSED_READY M512 H1024 shared='''+str(meta['shared'])+'''\\n");
}
static bool rec_fused_try(void* x, void* w, void* state, void* out,
        int B, int H, cudaStream_t stream) {
    if (!g_rec_fused_function || B != 512 || H != 1024) return false;
    assert(x != out);
    void* scratch = NULL;
    void* parameters[] = {&x, &w, &state, &out, &state, &scratch, &scratch};
    assert(cuLaunchKernel(g_rec_fused_function, 8, 32, 1, 128, 1, 1,
        '''+str(meta['shared'])+''', stream, parameters, NULL) == CUDA_SUCCESS);
    return true;
}
'''
(root/'rec_fused.cuh.generated').write_text(header)
print(json.dumps(meta,default=str),flush=True)
print(k.asm['ptx'][:2200],flush=True)
