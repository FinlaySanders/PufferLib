from pathlib import Path
r=Path('.')
s=(r/'source/ocean/nethack/nethack.cu').read_text()
def function(name):
 start=s.index('__global__ void '+name+'(')
 body=s.index('{',start);depth=1;j=body+1
 while depth:
  depth += (s[j]=='{')-(s[j]=='}');j+=1
 return s[start:j]+'\n'
pre='''#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cstdint>
using precision_t=__nv_bfloat16;
__device__ float to_float(precision_t x){return __bfloat162float(x);}
__device__ precision_t from_float(float x){return __float2bfloat16(x);}
constexpr int NH_MV=64,NH_CONCAT=1698;
__device__ __forceinline__ void nh_fxp_atomic_add(long long* addr,float v) {
 atomicAdd((unsigned long long*)addr,(unsigned long long)(long long)__float2ll_rn(v*16777216.0f));
}
'''
base=function('nh_min_dv_kernel')+function('nh_relu_bias_bwd_kernel')
(r/'pool_bwd_reference_parts.cu').write_text(pre+base)
