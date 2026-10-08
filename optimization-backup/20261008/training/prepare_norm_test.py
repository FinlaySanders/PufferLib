from pathlib import Path
r=Path(__file__).parent;a=(r/'source/src/algo.cu').read_text();p=(r/'source/src/pufferl.cu').read_text()
k=p[p.index('__device__ __forceinline__ void block_reduce_sum('):p.index('\n#endif',p.index('__device__ __forceinline__ void block_reduce_sum('))]
k+=a[a.index('__global__ void muon_sum_sq_partials'):a.index('// Global grad clip')]
k+=a[a.index('__global__ void muon_l2_normalize'):a.index('// dst = scale')]
k+=a[a.index('struct MuonNormDesc'):a.index('\n#endif',a.index('struct MuonNormDesc'))]
head='''#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <vector>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cmath>
typedef __nv_bfloat16 precision_t;
__device__ float to_float(precision_t x){return __bfloat162float(x);}
__device__ precision_t from_float(float x){return __float2bfloat16(x);}
'''
main='''
int main(){std::vector<int> ns={1,4,24,255,256,257,768,1024,4096,65535,65536,65537,191264,1048576,3145728};std::vector<MuonNormDesc>d;long n=0;for(int x:ns){d.push_back({n,x,std::min((x+255)/256,256)});n+=x;}
precision_t *x,*y;float *pa,*pb,*na,*nb;MuonNormDesc *ds;assert(cudaMalloc(&x,n*2)==0);assert(cudaMalloc(&y,n*2)==0);cudaMalloc(&pa,d.size()*256*4);cudaMalloc(&pb,d.size()*256*4);cudaMalloc(&na,d.size()*4);cudaMalloc(&nb,d.size()*4);cudaMalloc(&ds,d.size()*sizeof(MuonNormDesc));cudaMemcpy(ds,d.data(),d.size()*sizeof(MuonNormDesc),cudaMemcpyHostToDevice);
std::vector<precision_t>h(n),aa(n),bb(n);std::vector<float>an(d.size()),bn(d.size());
for(int pat=0;pat<5;pat++){for(long i=0;i<n;i++){float v=sin(i*.13)*cos(i*.031);if(pat==0)v=0;if(pat==2&&i%11)v=0;if(pat==3)v*=1e-15;if(pat==4)v*=1e12;h[i]=__float2bfloat16(v);}cudaMemcpy(x,h.data(),n*2,cudaMemcpyHostToDevice);cudaMemcpy(y,h.data(),n*2,cudaMemcpyHostToDevice);
for(int j=0;j<d.size();j++){auto z=d[j];muon_sum_sq_partials<<<z.blocks,256>>>(pa+j*256,x+z.offset,z.n);muon_sum_sq_reduce<<<1,256>>>(na+j,pa+j*256,z.blocks);muon_l2_normalize<<<(z.n+255)/256,256>>>(x+z.offset,na+j,1e-7f,z.n);}
muon_norm_batch_partials<<<dim3(256,d.size()),256>>>(pb,y,ds);muon_norm_batch_reduce<<<d.size(),256>>>(nb,pb,ds);muon_norm_batch_apply<<<dim3(256,d.size()),256>>>(y,nb,ds);assert(cudaDeviceSynchronize()==0);cudaMemcpy(aa.data(),x,n*2,cudaMemcpyDeviceToHost);cudaMemcpy(bb.data(),y,n*2,cudaMemcpyDeviceToHost);cudaMemcpy(an.data(),na,d.size()*4,cudaMemcpyDeviceToHost);cudaMemcpy(bn.data(),nb,d.size()*4,cudaMemcpyDeviceToHost);assert(!memcmp(an.data(),bn.data(),d.size()*4));assert(!memcmp(aa.data(),bb.data(),n*2));printf("pattern=%d params=%zu elements=%ld bitwise=PASS\\n",pat,d.size(),n);}}
'''
(r/'norm_test.cu').write_text(head+k+main)
