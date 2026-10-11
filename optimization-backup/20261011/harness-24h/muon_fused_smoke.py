from pathlib import Path
import hashlib
import json
import subprocess
import sys

r = Path(__file__).resolve().parent
d = r / (sys.argv[1] if len(sys.argv) > 1 else 'muon_fused_smoke')
assert not subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip()
d.mkdir(exist_ok=False)
prefix = r'''
#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublas_v2.h>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#define CU(x) do { cudaError_t e=(x); if(e!=cudaSuccess) {fprintf(stderr,"%s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e));abort();} } while(0)
#define BL(x) do { cublasStatus_t e=(x); if(e!=CUBLAS_STATUS_SUCCESS) {fprintf(stderr,"cuBLAS %d line %d\n",(int)e,__LINE__);abort();} } while(0)
using BF = __nv_bfloat16;
'''
main = r'''
cublasHandle_t handle;
void mm(cublasOperation_t oa,cublasOperation_t ob,int M,int N,int K,
        BF* A,BF* B,BF* C,float alpha=1.0f,float beta=0.0f) {
    int lda=oa==CUBLAS_OP_N?K:M,ldb=ob==CUBLAS_OP_N?N:K;
    BL(cublasGemmEx(handle,ob,oa,N,M,K,&alpha,B,CUDA_R_16BF,ldb,
       A,CUDA_R_16BF,lda,&beta,C,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT));
}
__global__ void scale_output(BF* out,BF* in,int n,float scale) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i<n) out[i]=__float2bfloat16(scale*__bfloat162float(in[i]));
}
void check(int R,int C,int mode,int seed) {
    int n=R*C,M=R<C?R:C;
    std::vector<BF> input(n),a(n),b(n);
    std::vector<float> initial(n);
    uint32_t rng=seed;double norm=0;
    for(int i=0;i<n;i++) {
        rng=1664525U*rng+1013904223U;
        float x=mode==0 ? 0.0f : mode==1 ? (float)((i/C)%7-3)*(float)((i%C)%5-2) : ((int)(rng%20001)-10000)*0.001f;
        initial[i]=x;norm+=(double)x*x;
    }
    for(int i=0;i<n;i++) input[i]=__float2bfloat16(initial[i]/(sqrt(norm)+1e-7));
    BF *x,*y,*g,*gb,*candidate,*reference;
    CU(cudaMalloc(&x,n*sizeof(BF)));CU(cudaMalloc(&y,n*sizeof(BF)));
    CU(cudaMalloc(&g,M*M*sizeof(BF)));CU(cudaMalloc(&gb,M*M*sizeof(BF)));
    CU(cudaMalloc(&candidate,n*sizeof(BF)));CU(cudaMalloc(&reference,n*sizeof(BF)));
    CU(cudaMemcpy(x,input.data(),n*sizeof(BF),cudaMemcpyHostToDevice));
    CU(cudaMemcpy(candidate,input.data(),n*sizeof(BF),cudaMemcpyHostToDevice));
    MuonFusedDesc desc={0,R,C},*dd;
    CU(cudaMalloc(&dd,sizeof(desc)));CU(cudaMemcpy(dd,&desc,sizeof(desc),cudaMemcpyHostToDevice));
    float co[5][3]={{4.0848f,-6.8946f,2.9270f},{3.9505f,-6.3029f,2.6377f},{3.7418f,-5.5913f,2.3037f},{2.8769f,-3.1427f,1.2046f},{2.8366f,-3.0525f,1.2012f}};
    for(int i=0;i<5;i++) {
        BF *src=i%2?y:x,*dst=i%2?x:y;
        if(R>C) mm(CUBLAS_OP_T,CUBLAS_OP_N,C,C,R,src,src,g);
        else mm(CUBLAS_OP_N,CUBLAS_OP_T,R,R,C,src,src,g);
        CU(cudaMemcpyAsync(gb,g,M*M*sizeof(BF),cudaMemcpyDeviceToDevice));
        mm(CUBLAS_OP_N,CUBLAS_OP_N,M,M,M,g,g,gb,co[i][2],co[i][1]);
        CU(cudaMemcpyAsync(dst,src,n*sizeof(BF),cudaMemcpyDeviceToDevice));
        if(R>C) mm(CUBLAS_OP_N,CUBLAS_OP_N,R,C,C,src,gb,dst,1.0f,co[i][0]);
        else mm(CUBLAS_OP_N,CUBLAS_OP_N,R,C,R,gb,src,dst,1.0f,co[i][0]);
    }
    scale_output<<<(n+255)/256,256>>>(reference,y,n,sqrtf(fmaxf(1.0f,(float)R/C)));
    muon_fused_small<<<1,256>>>(candidate,dd);
    CU(cudaGetLastError());CU(cudaDeviceSynchronize());
    CU(cudaMemcpy(a.data(),reference,n*sizeof(BF),cudaMemcpyDeviceToHost));
    CU(cudaMemcpy(b.data(),candidate,n*sizeof(BF),cudaMemcpyDeviceToHost));
    double sq=0,ref=0;float maxerr=0;int different=0;
    for(int i=0;i<n;i++) {
        float u=__bfloat162float(a[i]),v=__bfloat162float(b[i]);
        assert(std::isfinite(u)&&std::isfinite(v));
        double dx=(double)v-u;sq+=dx*dx;ref+=(double)u*u;maxerr=fmaxf(maxerr,fabsf(v-u));
        different+=memcmp(a.data()+i,b.data()+i,sizeof(BF))!=0;
    }
    double rel=sqrt(sq/fmax(ref,1e-30));
    printf("{\"R\":%d,\"C\":%d,\"mode\":%d,\"seed\":%d,\"count\":%d,\"different\":%d,\"max_abs\":%.9g,\"relative_l2\":%.9g}\n",R,C,mode,seed,n,different,maxerr,rel);
    fflush(stdout);
    // A layout/scale smoke gate, not proof of equivalent optimizer updates.
    assert(rel<0.05);
    for(void* p:{(void*)x,(void*)y,(void*)g,(void*)gb,(void*)candidate,(void*)reference,(void*)dd}) CU(cudaFree(p));
}
int main() {
    BL(cublasCreate(&handle));BL(cublasSetStream(handle,0));
    void* workspace;CU(cudaMalloc(&workspace,4UL<<20));
    BL(cublasSetWorkspace(handle,workspace,4UL<<20));BL(cublasSetMathMode(handle,CUBLAS_DEFAULT_MATH));
    int shapes[][2]={{14,32},{9,8},{16,32},{16,24},{16,36},{64,16},{64,64},{13,16},{5,8},{2,8},{3,8},{16,48},{16,16},{1,1},{1,64},{64,1},{7,63},{63,7},{31,33},{33,31},{63,64},{64,63}};
    for(auto& shape:shapes) for(int mode=0;mode<3;mode++) check(shape[0],shape[1],mode,101+mode);
    BL(cublasDestroy(handle));CU(cudaFree(workspace));
}
'''
src = d / 'test.cu'
src.write_text(prefix + (r/'muon_fused_small_kernels.cu.txt').read_text() + main)
command = ['nvcc', '-O3', '-arch=sm_89', '-std=c++17', str(src), '-lcublas', '-o', str(d/'test')]
(d/'command.json').write_text(json.dumps(command, indent=2))
with (d/'build.log').open('w') as f:
    subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, check=True)
with (d/'results.jsonl').open('w') as f:
    subprocess.run([str(d/'test')], stdout=f, stderr=subprocess.STDOUT, check=True)
rows = [json.loads(x) for x in (d/'results.jsonl').read_text().splitlines()]
summary = dict(cases=len(rows), values=sum(x['count'] for x in rows),
    different=sum(x['different'] for x in rows), max_relative_l2=max(x['relative_l2'] for x in rows),
    max_absolute=max(x['max_abs'] for x in rows), source_sha256=hashlib.sha256(src.read_bytes()).hexdigest())
(d/'summary.json').write_text(json.dumps(summary, indent=2))
print(summary, flush=True)
