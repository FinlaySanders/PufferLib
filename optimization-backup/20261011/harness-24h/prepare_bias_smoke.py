from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parent;s=(r/'source/ocean/nethack/nethack.cu').read_text()
def extract(name):
 pos=s.index(name+'(');start=s.rfind('\n',0,pos)+1;opened=s.index('{',pos);depth=1;i=opened+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[start:i]
kernels='\n\n'.join(extract(n) for n in ['nh_fxp_atomic_add','nh_relu_bias_bwd_kernel','nh_relu_bias_bwd_direct_kernel'])
header=r'''#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
typedef __nv_bfloat16 precision_t;
#define to_float __bfloat162float
#define from_float __float2bfloat16
static constexpr float NH_FXP = 16777216.0f;
'''
main=r'''
int main() {
 int cases=0;long long elements=0;
 for(int dim : {256,384,512,1024,2048})
 for(int rows : {1,17,257,4096})
 for(int mode=0;mode<3;mode++) {
  int total=rows*dim-(mode==2?7:0);
  int blocks=(total+255)/256;if(blocks>1024)blocks=1024;
  while((blocks*256)%dim)blocks++;
  std::vector<precision_t> g(total),o(total),left(total),right(total);
  std::vector<long long> seed(dim),a(dim),b(dim);
  for(int i=0;i<total;i++) {
   float x=(float)((i*997LL+3)%4093-2046)/1024.0f;
   if(mode==2)x=(i%2?-1.0f:1.0f)*(i%7?0.00006103515625f:128.0f);
   g[i]=__float2bfloat16(x);o[i]=__float2bfloat16(mode==0?1.0f:(i%3?1.0f:-1.0f));
  }
  for(int j=0;j<dim;j++)seed[j]=j*17-100;
  precision_t *ga,*gb,*out;long long *ba,*bb;
  assert(cudaMalloc(&ga,total*sizeof(precision_t))==cudaSuccess);
  assert(cudaMalloc(&gb,total*sizeof(precision_t))==cudaSuccess);
  assert(cudaMalloc(&out,total*sizeof(precision_t))==cudaSuccess);
  assert(cudaMalloc(&ba,dim*sizeof(long long))==cudaSuccess);
  assert(cudaMalloc(&bb,dim*sizeof(long long))==cudaSuccess);
  assert(cudaMemcpy(ga,g.data(),total*sizeof(precision_t),cudaMemcpyHostToDevice)==cudaSuccess);
  assert(cudaMemcpy(gb,g.data(),total*sizeof(precision_t),cudaMemcpyHostToDevice)==cudaSuccess);
  assert(cudaMemcpy(out,o.data(),total*sizeof(precision_t),cudaMemcpyHostToDevice)==cudaSuccess);
  assert(cudaMemcpy(ba,seed.data(),dim*sizeof(long long),cudaMemcpyHostToDevice)==cudaSuccess);
  assert(cudaMemcpy(bb,seed.data(),dim*sizeof(long long),cudaMemcpyHostToDevice)==cudaSuccess);
  nh_relu_bias_bwd_kernel<<<blocks,256,dim*sizeof(long long)>>>(ga,out,ba,total,dim);
  nh_relu_bias_bwd_direct_kernel<<<blocks,256>>>(gb,out,bb,total,dim);
  assert(cudaDeviceSynchronize()==cudaSuccess);
  assert(cudaMemcpy(left.data(),ga,total*sizeof(precision_t),cudaMemcpyDeviceToHost)==cudaSuccess);
  assert(cudaMemcpy(right.data(),gb,total*sizeof(precision_t),cudaMemcpyDeviceToHost)==cudaSuccess);
  assert(cudaMemcpy(a.data(),ba,dim*sizeof(long long),cudaMemcpyDeviceToHost)==cudaSuccess);
  assert(cudaMemcpy(b.data(),bb,dim*sizeof(long long),cudaMemcpyDeviceToHost)==cudaSuccess);
  assert(memcmp(left.data(),right.data(),total*sizeof(precision_t))==0);
  assert(a==b);
  cudaFree(ga);cudaFree(gb);cudaFree(out);cudaFree(ba);cudaFree(bb);
  cases++;elements+=total;
 }
 printf("BIAS_DIRECT_SMOKE cases=%d elements=%lld exact=1\n",cases,elements);
}
'''
out=r/'bias_direct_smoke.cu';out.write_text(header+kernels+main)
(r/'BIAS_DIRECT_SMOKE_SOURCE.json').write_text(json.dumps(dict(actual_kernel_extraction=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),smoke_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),scope='Five wide column counts; short/long and partial grids; dense/sparse masks and cancellation. Compares exact BF16 masked gradients and fixed-point sums. No claim of whole-model equivalence from this unit check.'),indent=2))
print('Prepared60case direct-kernel smoke source; not compiled or run.')
