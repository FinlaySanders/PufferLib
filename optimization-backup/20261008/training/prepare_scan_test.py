from pathlib import Path
r=Path(__file__).parent;b=(r/'algo.baseline.cu').read_text();s=(r/'source/src/algo.cu').read_text()
def fn(text,name):
 i=text.index('__global__ void '+name+'(');j=text.index('\n}\n',i)+3;return text[i:j]
i=b.index('__device__ __forceinline__ float sigmoid(');j=b.index('// Rollout MinGRU',i)
code='''#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <cmath>
using precision_t=__nv_bfloat16;
struct Prec { precision_t* data; };
__host__ __device__ float to_float(precision_t v){return __bfloat162float(v);}
__host__ __device__ precision_t from_float(float v){return __float2bfloat16_rn(v);}
#define MINGRU_TILE 32
'''+b[i:j]+b[b.index('struct PrefixScan {'):b.index('// Train scan:')]
for name in ['mingru_scan_forward_row','mingru_scan_backward_row']:code+=fn(b,name).replace(name,name+'_reference')
code+='\n#define PUF_SCAN_PACK\n#ifndef PUF_MINGRU_LOAD_ROWS\n#define PUF_MINGRU_LOAD_ROWS 8\n#endif\n'
for name in ['mingru_scan_forward_row','mingru_scan_backward_row']:code+=fn(s,name)
code+=r'''
std::vector<void*> allocated;
precision_t* buf(int n,bool randomize=false) {
 precision_t* p;assert(cudaMallocManaged(&p,n*sizeof(*p))==cudaSuccess);allocated.push_back(p);
 for(int i=0;i<n;i++)p[i]=from_float(randomize?(rand()%4001-2000)/100.f:0.f);return p;
}
void cmp(const char* name,precision_t* a,precision_t* b,int n) {
 for(int i=0;i<n;i++)if(memcmp(a+i,b+i,2)){printf("FAIL %s i=%d %.9g %.9g\n",name,i,to_float(a[i]),to_float(b[i]));exit(1);}
}
int main() {
 int cases[][3]={{1,1,1},{2,31,17},{3,33,65},{8,512,1024},{16,128,224},{5,257,31}};
 for(auto& c:cases)for(int resets=0;resets<2;resets++) {
  int B=c[0],T=c[1],H=c[2],n=B*T*H;PrefixScan a={},b={};a.B=b.B=B;a.T=b.T=T;a.H=b.H=H;
  a.combined_ptr=b.combined_ptr=buf(3*n,true);a.state_ptr=b.state_ptr=buf(B*H,true);a.input_ptr=b.input_ptr=buf(n,true);
  if(resets) {a.terminals_ptr=b.terminals_ptr=buf(B*T);for(int t=0;t<B*T;t++)a.terminals_ptr[t]=from_float(rand()%7==0?1.f:0.f);}
  for(auto* p:{&a,&b}) {p->scan_h={buf(n)};p->out={buf(n)};p->next_state={buf(B*H)};p->grad_combined={buf(3*n)};p->grad_input={buf(n)};p->grad_state={buf(B*H)};}
  auto* go=buf(n,true);auto* gs=buf(B*H,true);dim3 grid(B,(H+31)/32);
  mingru_scan_forward_row_reference<<<grid,dim3(32,32)>>>(a);
  mingru_scan_forward_row<<<grid,dim3(32,PUF_MINGRU_LOAD_ROWS)>>>(b);
  mingru_scan_backward_row_reference<<<grid,dim3(32,32)>>>(a,go,gs);
  mingru_scan_backward_row<<<grid,dim3(32,PUF_MINGRU_LOAD_ROWS)>>>(b,go,gs);
  assert(cudaDeviceSynchronize()==cudaSuccess);
  cmp("h",a.scan_h.data,b.scan_h.data,n);cmp("out",a.out.data,b.out.data,n);cmp("state",a.next_state.data,b.next_state.data,B*H);
  cmp("dc",a.grad_combined.data,b.grad_combined.data,3*n);cmp("dx",a.grad_input.data,b.grad_input.data,n);cmp("ds",a.grad_state.data,b.grad_state.data,B*H);
  printf("PASS B=%d T=%d H=%d resets=%d\n",B,T,H,resets);
  for(void* p:allocated)cudaFree(p);allocated.clear();
 }
}
'''
(r/'scan_test.cu').write_text(code)
