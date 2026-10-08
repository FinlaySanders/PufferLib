#pragma once
#include <cuda_bf16.h>
#include <cublas_v2.h>
#include <cassert>
__global__ void split_finish(const float* partial, __nv_bfloat16* out, int count, int parts, float alpha, float beta) {
    int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=count)return;
    float v=0;for(int s=0;s<parts;s++)v+=partial[s*count+i];
    out[i]=__float2bfloat16(alpha*v+(beta?beta*__bfloat162float(out[i]):0.0f));
}
static void split_mm(cublasHandle_t h,int M,int N,int K,const void*A,const void*B,void*C,float*tmp,cudaStream_t stream,int parts,float alpha=1,float beta=0) {
    assert(K%parts==0);int k=K/parts;float one=1,zero=0;cublasSetStream(h,stream);
    auto status=cublasGemmStridedBatchedEx(h,CUBLAS_OP_N,CUBLAS_OP_T,N,M,k,&one,B,CUDA_R_16BF,N,(long long)k*N,A,CUDA_R_16BF,M,(long long)k*M,&zero,tmp,CUDA_R_32F,N,(long long)M*N,parts,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT);
    assert(status==CUBLAS_STATUS_SUCCESS);
    split_finish<<<(M*N+255)/256,256,0,stream>>>(tmp,(__nv_bfloat16*)C,M*N,parts,alpha,beta);
}
