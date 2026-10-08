#pragma once
#include <set>
#include <tuple>
#include <vector>
__global__ void gc_convert(const __nv_bfloat16*a,float*b,int n){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)b[i]=__bfloat162float(a[i]);}
static void actual_gradient_check(cublasHandle_t h,int M,int N,int K,const void*A,const void*B,const void*C,cudaStream_t st,float alpha) {
    static thread_local std::set<std::tuple<int,int,int>> checked;
    if(!checked.insert({M,N,K}).second)return;
    float *af,*bf,*ref;cudaMalloc(&af,(size_t)M*K*4);cudaMalloc(&bf,(size_t)N*K*4);cudaMalloc(&ref,M*N*4);
    gc_convert<<<(M*K+255)/256,256,0,st>>>((const __nv_bfloat16*)A,af,M*K);gc_convert<<<(N*K+255)/256,256,0,st>>>((const __nv_bfloat16*)B,bf,N*K);float zero=0;
    assert(cublasGemmEx(h,CUBLAS_OP_N,CUBLAS_OP_T,N,M,K,&alpha,bf,CUDA_R_32F,N,af,CUDA_R_32F,M,&zero,ref,CUDA_R_32F,N,CUBLAS_COMPUTE_32F_PEDANTIC,CUBLAS_GEMM_DEFAULT)==CUBLAS_STATUS_SUCCESS);
    assert(cudaStreamSynchronize(st)==cudaSuccess);std::vector<float>r(M*N);std::vector<__nv_bfloat16>c(M*N);cudaMemcpy(r.data(),ref,M*N*4,cudaMemcpyDeviceToHost);cudaMemcpy(c.data(),C,M*N*2,cudaMemcpyDeviceToHost);
    double sq=0,err=0,mx=0;for(int i=0;i<M*N;i++){double x=r[i],e=__bfloat162float(c[i])-x;sq+=x*x;err+=e*e;mx=fmax(mx,fabs(e));}
    double rel=sqrt(err/fmax(sq,1e-30)),maxr=mx/sqrt(fmax(sq/(M*N),1e-30));int violations=0;double rms=sqrt(fmax(sq/(M*N),1e-30));for(int i=0;i<M*N;i++)if(fabs(__bfloat162float(c[i])-r[i])>.004*fabs(r[i])+.001*rms)violations++;fprintf(stderr,"GEMMCHECK M=%d N=%d K=%d rel=%.9g max_rms=%.9g\n",M,N,K,rel,maxr);fprintf(stderr,"GEMMROUND violations=%d\n",violations);assert(isfinite(rel)&&rel<.003&&violations==0);
    cudaFree(af);cudaFree(bf);cudaFree(ref);
}
