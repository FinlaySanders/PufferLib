from pathlib import Path
r=Path(__file__).parent;s=(r/'source/src/pufferl.cu').read_text();i=s.index('__global__ void transpose_102(precision_t*');j=s.index('\n}',i)+2
code='''#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cstdint>
#include <cassert>
#include <cstdio>
using precision_t=__nv_bfloat16;
'''+s[i:j]+r'''
int main(){int A=17,B=33,C=129,N=A*B*C;uint16_t *a,*b;
assert(cudaMallocManaged(&a,N*2)==cudaSuccess);assert(cudaMallocManaged(&b,N*2)==cudaSuccess);
for(int i=0;i<N;i++){a[i]=(uint16_t)i;b[i]=0;}
transpose_102<<<(N+255)/256,256>>>((precision_t*)b,(precision_t*)a,A,B,C);assert(cudaDeviceSynchronize()==cudaSuccess);
for(int i=0;i<N;i++){int aa=i/(B*C),bb=(i/C)%B,cc=i%C;assert(b[(bb*A+aa)*C+cc]==a[i]);}
printf("PASS all65536 byte-pair bit patterns survive packed transpose, N=%d\n",N);cudaFree(a);cudaFree(b);
}
'''
(r/'byte_test.cu').write_text(code)
