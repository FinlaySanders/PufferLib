from pathlib import Path
import json,hashlib,subprocess,re
import torch
from inventory_fused_screen import inventory_fused

assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
r=Path(__file__).resolve().parent
p=torch.empty(1,device='cuda',dtype=torch.bfloat16)
g=torch.empty(1,device='cuda',dtype=torch.float32)
k=inventory_fused.warmup(p,p,p,p,p,g,p,g,p,p,False,False,grid=(512,),num_warps=4,num_stages=2)
meta=k.metadata._asdict()
assert meta['global_scratch_size']==meta['profile_scratch_size']==0
entry=k.asm['ptx'].split('.entry inventory_fused(',1)[1].split(')',1)[0]
assert len(re.findall(r'\.param',entry))==12,entry
data=k.asm['cubin']
(r/'inventory_fused.cubin').write_bytes(data)
(r/'inventory_fused.ptx').write_text(k.asm['ptx'])
(r/'INVENTORY_FUSED_EXPORT.json').write_text(json.dumps(dict(metadata=meta,cubin_sha256=hashlib.sha256(data).hexdigest(),source_sha256=hashlib.sha256((r/'inventory_fused_screen.py').read_bytes()).hexdigest()),indent=2,default=str))
array='\n'.join(','.join(str(x) for x in data[i:i+24])+',' for i in range(0,len(data),24))
header='''#include <cuda.h>
// Isolated inference-only inventory MLP/pool prototype; logical architecture unchanged.
static const unsigned char inventory_fused_cubin[] = {
'''+array+'''
};
thread_local CUmodule g_inventory_fused_module = NULL;
thread_local CUfunction g_inventory_fused_function = NULL;
static void inventory_fused_init() {
    if (!getenv("NH_INVENTORY_FUSED") || !atoi(getenv("NH_INVENTORY_FUSED"))) return;
    if (g_inventory_fused_function) return;
    int device;
    cudaDeviceProp properties;
    assert(cudaGetDevice(&device) == cudaSuccess);
    assert(cudaGetDeviceProperties(&properties, device) == cudaSuccess);
    assert(properties.major == 8 && properties.minor == 9);
    assert(cuModuleLoadData(&g_inventory_fused_module, inventory_fused_cubin) == CUDA_SUCCESS);
    assert(cuModuleGetFunction(&g_inventory_fused_function, g_inventory_fused_module, "inventory_fused") == CUDA_SUCCESS);
    fprintf(stderr,"INVENTORY_FUSED_READY shared='''+str(meta['shared'])+'''\\n");
}
static bool inventory_fused_try(void* x, void* w1, void* b1, void* w2, void* b2,
        void* gid, void* concat, void* amax, void* h1, void* v, int B, cudaStream_t stream) {
    if (!g_inventory_fused_function) return false;
    void* scratch = NULL;
    void* args[] = {&x,&w1,&b1,&w2,&b2,&gid,&concat,&amax,&h1,&v,&scratch,&scratch};
    assert(cuLaunchKernel(g_inventory_fused_function, B, 1, 1, 128, 1, 1,
        '''+str(meta['shared'])+''', stream, args, NULL) == CUDA_SUCCESS);
    return true;
}
'''
(r/'inventory_fused.cuh.generated').write_text(header)
print(json.dumps(meta,default=str),flush=True)
