from pathlib import Path
import hashlib
import json
import subprocess
import sys

r = Path(__file__).resolve().parent
d = r / (sys.argv[1] if len(sys.argv)>1 else 'scan_register_smoke')
d.mkdir(exist_ok=False)
s = (r / 'source/src/algo.cu').read_text()
helpers = s[s.index('__device__ __forceinline__ float sigmoid('):s.index('// Rollout MinGRU step:')]
kernels = s[s.index('struct PrefixScan {'):s.index('// Coalesced T-tile load')]
prefix = r'''
#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <vector>
using precision_t = __nv_bfloat16;
struct Prec { precision_t* data = NULL; };
__device__ __forceinline__ float to_float(precision_t x) { return __bfloat162float(x); }
__device__ __forceinline__ precision_t from_float(float x) { return __float2bfloat16(x); }
#define CU(x) do { cudaError_t e=(x); if(e != cudaSuccess) {fprintf(stderr,"%s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e));abort();} } while(0)
'''
main = r'''
std::vector<void*> allocations;
precision_t* data(int n, int seed, bool terminal = false) {
    precision_t* p;
    CU(cudaMallocManaged(&p, n * sizeof(*p)));
    allocations.push_back(p);
    uint32_t rng=seed;
    for (int i=0;i<n;i++) {
        rng=rng*1664525U+1013904223U;
        float x=terminal ? (rng%11 == 0 ? 1.0f : 0.0f) : ((int)(rng%20001)-10000)*0.001f;
        p[i]=__float2bfloat16(x);
    }
    return p;
}
struct Error { size_t n=0,diff=0; double sq=0,ref=0; float max=0; };
void compare(Error& e, precision_t* a, precision_t* b, int n) {
    for(int i=0;i<n;i++) {
        float x=__bfloat162float(a[i]),y=__bfloat162float(b[i]);
        assert(std::isfinite(x) && std::isfinite(y));
        e.n++;e.diff+=memcmp(a+i,b+i,sizeof(*a)) != 0;
        double dx=(double)y-x;e.sq+=dx*dx;e.ref+=(double)x*x;
        e.max=fmaxf(e.max,fabsf(y-x));
    }
}
template<int TILE> void check(int B,int T,int H,int terminals) {
    int n=B*T*H, ns=B*H;
    PrefixScan a,b;
    a.B=B;a.T=T;a.H=H;
    a.combined_ptr=data(3*n,1);a.input_ptr=data(n,2);a.state_ptr=data(ns,3);
    a.terminals_ptr=terminals ? data(B*T,4,true) : NULL;
    if(terminals==2) for(int i=0;i<B*T;i++) a.terminals_ptr[i]=__float2bfloat16(1.0f);
    b=a;
    a.out.data=data(n,5);a.scan_h.data=data(n,6);a.next_state.data=data(ns,7);
    b.out.data=data(n,8);b.scan_h.data=data(n,9);b.next_state.data=data(ns,10);
    a.grad_combined.data=data(3*n,11);a.grad_input.data=data(n,12);a.grad_state.data=data(ns,13);
    b.grad_combined.data=data(3*n,14);b.grad_input.data=data(n,15);b.grad_state.data=data(ns,16);
    precision_t* go=data(n,17),*gn=data(ns,18);
    mingru_scan_forward<<<(ns+255)/256,256>>>(a);
    mingru_scan_forward_regs<TILE><<<(ns+127)/128,128>>>(b);
    CU(cudaGetLastError());CU(cudaDeviceSynchronize());
    Error fwd,bwd;
    compare(fwd,a.out.data,b.out.data,n);compare(fwd,a.scan_h.data,b.scan_h.data,n);
    compare(fwd,a.next_state.data,b.next_state.data,ns);
    mingru_scan_backward<<<(ns+255)/256,256>>>(a,go,gn);
    mingru_scan_backward_regs<TILE><<<(ns+127)/128,128>>>(b,go,gn);
    CU(cudaGetLastError());CU(cudaDeviceSynchronize());
    compare(bwd,a.grad_combined.data,b.grad_combined.data,3*n);
    compare(bwd,a.grad_input.data,b.grad_input.data,n);compare(bwd,a.grad_state.data,b.grad_state.data,ns);
    printf("{\"tile\":%d,\"B\":%d,\"T\":%d,\"H\":%d,\"terminals\":%d,\"fwd_count\":%zu,\"fwd_different\":%zu,\"fwd_max\":%.9g,\"fwd_relative_l2\":%.9g,\"bwd_count\":%zu,\"bwd_different\":%zu,\"bwd_max\":%.9g,\"bwd_relative_l2\":%.9g}\n",TILE,B,T,H,terminals,fwd.n,fwd.diff,fwd.max,sqrt(fwd.sq/fmax(fwd.ref,1e-30)),bwd.n,bwd.diff,bwd.max,sqrt(bwd.sq/fmax(bwd.ref,1e-30)));
    fflush(stdout);
    // Diagnose compiler contraction with paired default and --fmad=false builds.
    // Numerical screening permits rounding, as authorized; these are not claims
    // of identical updates or stable training. Preserve the failed exact test.
    assert(sqrt(fwd.sq/fmax(fwd.ref,1e-30)) < 0.002);
    assert(sqrt(bwd.sq/fmax(bwd.ref,1e-30)) < 0.002);
    for(void* p:allocations) CU(cudaFree(p));allocations.clear();
}
int main() {
    int shapes[][3]={{1,1,7},{3,7,65},{2,16,32},{2,127,129},{32,128,1024},{3,129,65}};
    for(auto& shape:shapes) for(int term=0;term<3;term++) {
        check<2>(shape[0],shape[1],shape[2],term);
        check<4>(shape[0],shape[1],shape[2],term);
        check<8>(shape[0],shape[1],shape[2],term);
    }
}
'''
src = d / 'test.cu'
src.write_text(prefix + helpers + kernels + main)
command = ['nvcc','-O2','-arch=sm_89','-std=c++17',*sys.argv[2:],str(src),'-o',str(d/'test')]
(d/'command.json').write_text(json.dumps(command,indent=2))
with (d/'build.log').open('w') as f:
    subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
with (d/'results.jsonl').open('w') as f:
    subprocess.run([str(d/'test')],stdout=f,stderr=subprocess.STDOUT,check=True)
rows=[json.loads(x) for x in (d/'results.jsonl').read_text().splitlines()]
summary={'cases':len(rows),'forward_values':sum(x['fwd_count'] for x in rows),
    'backward_values':sum(x['bwd_count'] for x in rows),
    'forward_different':sum(x['fwd_different'] for x in rows),
    'backward_different':sum(x['bwd_different'] for x in rows),
    'max_forward_relative_l2':max(x['fwd_relative_l2'] for x in rows),
    'max_backward_relative_l2':max(x['bwd_relative_l2'] for x in rows),
    'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
(d/'summary.json').write_text(json.dumps(summary,indent=2))
print(summary,flush=True)
