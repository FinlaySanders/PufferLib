from pathlib import Path
import json,hashlib,subprocess
r=Path(__file__).resolve().parent;d=r/'outplace_rank_smoke';d.mkdir(exist_ok=False)
s=(r/'source/src/algo.cu').read_text();a=s.index('struct OutplacePlan');b=s.index('\n#endif',a)
body=s[a:b]
prefix=r'''
#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublas_v2.h>
#include <cublasLt.h>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#define CU(x) do { cudaError_t e=(x); if(e!=cudaSuccess) {fprintf(stderr,"%s:%d %s\n",__FILE__,__LINE__,cudaGetErrorString(e));abort();} } while(0)
using BF=__nv_bfloat16;
struct Prec{BF* data;long shape[2];};
struct CS{cudaStream_t stream;void* workspace;};
CS g_cublas_streams[1];int g_num_cublas_streams=1;
'''
main=r'''
uint32_t rng=931;
float value(){rng=1664525U*rng+1013904223U;return ((int)(rng%2001)-1000)*0.0002f;}
void check(cublasHandle_t h,int M,int N,int K,int rank){
 size_t na=(size_t)M*K,nb=(size_t)K*N,n=(size_t)M*N;
 std::vector<BF>a(na),b(nb),c(n),out(n),ref(n),readback(n);
 for(auto&x:a)x=__float2bfloat16(value());for(auto&x:b)x=__float2bfloat16(value());for(auto&x:c)x=__float2bfloat16(value());
 BF *ad,*bd,*cd,*dd,*rd;CU(cudaMalloc(&ad,na*2));CU(cudaMalloc(&bd,nb*2));CU(cudaMalloc(&cd,n*2));CU(cudaMalloc(&dd,n*2));CU(cudaMalloc(&rd,n*2));
 CU(cudaMemcpy(ad,a.data(),na*2,cudaMemcpyHostToDevice));CU(cudaMemcpy(bd,b.data(),nb*2,cudaMemcpyHostToDevice));CU(cudaMemcpy(cd,c.data(),n*2,cudaMemcpyHostToDevice));CU(cudaMemcpy(rd,c.data(),n*2,cudaMemcpyHostToDevice));
 float alpha=2.6377f,beta=-6.3029f;
 assert(cublasGemmEx(h,CUBLAS_OP_N,CUBLAS_OP_N,N,M,K,&alpha,bd,CUDA_R_16BF,N,ad,CUDA_R_16BF,K,&beta,rd,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT)==CUBLAS_STATUS_SUCCESS);
 Prec A={ad,{M,K}},B={bd,{K,N}},C={cd,{M,N}},D={dd,{M,N}};
 outplace_mm(&A,&B,&C,&D,0,alpha,beta);CU(cudaDeviceSynchronize());
 CU(cudaMemcpy(ref.data(),rd,n*2,cudaMemcpyDeviceToHost));CU(cudaMemcpy(out.data(),dd,n*2,cudaMemcpyDeviceToHost));CU(cudaMemcpy(readback.data(),cd,n*2,cudaMemcpyDeviceToHost));
 assert(memcmp(c.data(),readback.data(),n*2)==0);
 size_t different=0;double sq=0,norm=0;float maxerr=0;
 for(size_t i=0;i<n;i++){float x=__bfloat162float(ref[i]),y=__bfloat162float(out[i]);assert(std::isfinite(x)&&std::isfinite(y));different+=memcmp(&ref[i],&out[i],2)!=0;double e=(double)y-x;sq+=e*e;norm+=(double)x*x;maxerr=fmaxf(maxerr,fabsf(y-x));}
 double rel=sqrt(sq/fmax(norm,1e-30));assert(rel<0.01);
 printf("{\"M\":%d,\"N\":%d,\"K\":%d,\"rank\":%d,\"values\":%zu,\"different\":%zu,\"relative_l2\":%.9g,\"max_abs\":%.9g,\"input_C_unchanged\":true}\n",M,N,K,rank,n,different,rel,maxerr);fflush(stdout);
 for(void*p:{(void*)ad,(void*)bd,(void*)cd,(void*)dd,(void*)rd})CU(cudaFree(p));
}
int main(){
 cublasHandle_t h;assert(cublasCreate(&h)==CUBLAS_STATUS_SUCCESS);void*ws;CU(cudaMalloc(&ws,4UL<<20));g_cublas_streams[0]={0,ws};assert(cublasSetStream(h,0)==CUBLAS_STATUS_SUCCESS);assert(cublasSetWorkspace(h,ws,4UL<<20)==CUBLAS_STATUS_SUCCESS);assert(cublasSetMathMode(h,CUBLAS_DEFAULT_MATH)==CUBLAS_STATUS_SUCCESS);
 int shapes[][3]={{16,32,16},{64,64,64},{256,648,256},{1024,1024,1024},{3072,1024,1024},{1024,1698,1024}};
 for(int rank=0;rank<4;rank++){
  char s[8];snprintf(s,sizeof(s),"%d",rank);setenv("PUF_OUTPLACE_RANK",s,1);
  for(auto&shape:shapes)check(h,shape[0],shape[1],shape[2],rank);
  for(auto&p:outplace_plans){cublasLtMatmulDescDestroy(p.desc);cublasLtMatrixLayoutDestroy(p.a);cublasLtMatrixLayoutDestroy(p.b);cublasLtMatrixLayoutDestroy(p.c);}outplace_plans.clear();
 }
 cublasLtDestroy(outplace_handle);cublasDestroy(h);CU(cudaFree(ws));
}
'''
src=d/'test.cu';src.write_text(prefix+body+main)
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
cmd=['nvcc','-O2','-arch=sm_89','-std=c++17',str(src),'-lcublas','-lcublasLt','-o',str(d/'test')];(d/'command.json').write_text(json.dumps(cmd))
with (d/'build.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
with (d/'results.jsonl').open('w') as f, (d/'run.log').open('w') as log:subprocess.run([str(d/'test')],stdout=f,stderr=log,check=True)
rows=[json.loads(x) for x in (d/'results.jsonl').read_text().splitlines()]
summary=dict(cases=len(rows),values=sum(x['values']for x in rows),different=sum(x['different']for x in rows),max_relative_l2=max(x['relative_l2']for x in rows),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),scope='Basic finite/layout/scale smoke, not training update equivalence')
(d/'summary.json').write_text(json.dumps(summary,indent=2));print(summary,flush=True)
