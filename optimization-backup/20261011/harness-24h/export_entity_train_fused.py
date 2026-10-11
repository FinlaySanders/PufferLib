from pathlib import Path
import json,hashlib,subprocess,re
import torch,triton
from entity_train_fused import entity_train_fused

assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
r=Path(__file__).resolve().parent
p=torch.empty(1,device='cuda',dtype=torch.bfloat16);g=torch.empty(1,device='cuda')
cases=[('inventory',55,1010,5976,.2),('monster',16,1394,-1,.25),('item',16,1538,-1,.25),('spell',8,838,-1,.25)]
arrays=[];metas=[]
for i,(name,n,off,pad,eps) in enumerate(cases):
    results=json.loads((r/('ENTITY_TRAIN_'+name+'.json')).read_text())
    best=min([v for v in results['rows'] if v['config']],key=lambda v:v['microseconds'])
    assert best['microseconds']<min(v['microseconds'] for v in results['rows'] if v['config'] is None)
    warps,stages=best['config']
    k=entity_train_fused.warmup(p,p,p,p,p,g,p,g,p,p,n,max(16,triton.next_power_of_2(n)),pad,off,eps,grid=(4096,),num_warps=warps,num_stages=stages)
    meta=k.metadata._asdict()
    assert meta['global_scratch_size']==meta['profile_scratch_size']==0
    entry=k.asm['ptx'].split('.entry entity_train_fused(',1)[1].split(')',1)[0]
    assert len(re.findall(r'\.param',entry))==12
    data=k.asm['cubin']
    (r/('entity_train_fused_'+name+'.cubin')).write_bytes(data)
    (r/('entity_train_fused_'+name+'.ptx')).write_text(k.asm['ptx'])
    vals='\n'.join(','.join(str(x) for x in data[j:j+24])+',' for j in range(0,len(data),24))
    arrays.append('static const unsigned char entity_train_fused_'+name+'_cubin[] = {\n'+vals+'\n};\n')
    metas.append(dict(name=name,metadata=meta,cubin_sha256=hashlib.sha256(data).hexdigest()))
header='#include <cuda.h>\n'+''.join(arrays)+'''
thread_local CUmodule g_entity_train_fused_modules[4] = {};
thread_local CUfunction g_entity_train_fused_functions[4] = {};
static const unsigned int entity_train_fused_shared[4] = {'''+','.join(str(x['metadata']['shared']) for x in metas)+'''};
static const unsigned int entity_train_fused_threads[4] = {'''+','.join(str(x['metadata']['num_warps']*32) for x in metas)+'''};
static void entity_train_fused_init() {
    int mask = getenv("NH_ENTITY_TRAIN_FUSED") ? atoi(getenv("NH_ENTITY_TRAIN_FUSED")) : 0;
    if (!mask) return;
    int device; cudaDeviceProp properties;
    assert(cudaGetDevice(&device) == cudaSuccess);
    assert(cudaGetDeviceProperties(&properties, device) == cudaSuccess);
    assert(properties.major == 8 && properties.minor == 9);
    const void* data[4] = {'''+','.join('entity_train_fused_'+x['name']+'_cubin' for x in metas)+'''};
    for (int i=0; i<4; i++) {
        if (!(mask & (1<<i)) || g_entity_train_fused_functions[i]) continue;
        assert(cuModuleLoadData(&g_entity_train_fused_modules[i], data[i]) == CUDA_SUCCESS);
        assert(cuModuleGetFunction(&g_entity_train_fused_functions[i], g_entity_train_fused_modules[i], "entity_train_fused") == CUDA_SUCCESS);
        fprintf(stderr,"ENTITY_TRAIN_READY branch=%d shared=%u\\n",i,entity_train_fused_shared[i]);
    }
}
static bool entity_train_fused_try(int branch, void* x, void* w1, void* b1, void* w2,
        void* b2, void* gid, void* concat, void* amax, void* h1, void* v, int B, cudaStream_t stream) {
    CUfunction f = g_entity_train_fused_functions[branch];
    if (!f) return false;
    void* scratch = NULL;
    void* args[] = {&x,&w1,&b1,&w2,&b2,&gid,&concat,&amax,&h1,&v,&scratch,&scratch};
    assert(cuLaunchKernel(f,B,1,1,entity_train_fused_threads[branch],1,1,
        entity_train_fused_shared[branch],stream,args,NULL) == CUDA_SUCCESS);
    return true;
}
'''
(r/'entity_train_fused.cuh.generated').write_text(header)
(r/'ENTITY_TRAIN_EXPORT.json').write_text(json.dumps(dict(kernels=metas,source_sha256=hashlib.sha256((r/'entity_train_fused.py').read_bytes()).hexdigest()),indent=2,default=str))
print([(m['name'],m['metadata']['shared'],m['metadata']['num_warps']) for m in metas],flush=True)
