#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublas_v2.h>
#include <cublasLt.h>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <cmath>
#include <vector>
#include <algorithm>
#define CU(x) assert((x)==cudaSuccess)
#define BL(x) assert((x)==CUBLAS_STATUS_SUCCESS)
#define CUBLAS_PRECISION CUDA_R_16BF
using bf16=__nv_bfloat16;
thread_local cublasLtHandle_t g_rec_lt;
struct CublasStream {cudaStream_t stream; void* workspace;};
thread_local CublasStream g_cublas_streams[1];
thread_local int g_num_cublas_streams=1;
#include "source/src/train_dw_lt.cuh"
__global__ void init_values(bf16* p,size_t n,uint32_t seed) {
 size_t i=(size_t)blockIdx.x*blockDim.x+threadIdx.x;
 if(i<n) {uint32_t x=(uint32_t)i*1664525u+seed;x^=x>>13;p[i]=__float2bfloat16(((int)(x%257)-128)/128.0f);}
}
int main(){
 CU(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));
 cudaStream_t stream;CU(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
 void* ws;CU(cudaMalloc(&ws,4u<<20));g_cublas_streams[0]={stream,ws};
 BL(cublasLtCreate(&g_rec_lt));cublasHandle_t h;BL(cublasCreate(&h));
 BL(cublasSetStream(h,stream));BL(cublasSetWorkspace(h,ws,4u<<20));BL(cublasSetMathMode(h,CUBLAS_DEFAULT_MATH));
 const int M=3072,N=1024,K=4096;bf16 *a,*b,*c;
 CU(cudaMalloc(&a,(size_t)M*K*2));CU(cudaMalloc(&b,(size_t)N*K*2));CU(cudaMalloc(&c,(size_t)M*N*2));
 std::vector<bf16> ref((size_t)M*N),got(ref.size());float alpha=1,beta=0;
 unsetenv("NH_TRAIN_DW_LT");assert(!train_dw_lt_try(CUBLAS_OP_T,CUBLAS_OP_N,M,N,K,a,b,c,stream,alpha,beta));
 setenv("NH_TRAIN_DW_LT","1",1);
 assert(!train_dw_lt_try(CUBLAS_OP_N,CUBLAS_OP_T,M,N,K,a,b,c,stream,alpha,beta));
 assert(!train_dw_lt_try(CUBLAS_OP_T,CUBLAS_OP_N,M,N,K,a,b,c,stream,alpha,1));
 assert(!train_dw_lt_try(CUBLAS_OP_T,CUBLAS_OP_N,M,N,K,a+1,b,c,stream,alpha,beta));
 for(int seed:{713,1779}) {
 init_values<<<((size_t)M*K+255)/256,256,0,stream>>>(a,(size_t)M*K,seed);
 init_values<<<((size_t)N*K+255)/256,256,0,stream>>>(b,(size_t)N*K,seed+284);
 BL(cublasGemmEx(h,CUBLAS_OP_N,CUBLAS_OP_T,N,M,K,&alpha,b,CUDA_R_16BF,N,a,CUDA_R_16BF,M,&beta,c,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT));
 CU(cudaStreamSynchronize(stream));CU(cudaMemcpy(ref.data(),c,ref.size()*2,cudaMemcpyDeviceToHost));
 assert(train_dw_lt_try(CUBLAS_OP_T,CUBLAS_OP_N,M,N,K,a,b,c,stream,alpha,beta));
 cudaGraph_t graph;cudaGraphExec_t exec;CU(cudaStreamBeginCapture(stream,cudaStreamCaptureModeThreadLocal));
 assert(train_dw_lt_try(CUBLAS_OP_T,CUBLAS_OP_N,M,N,K,a,b,c,stream,alpha,beta));
 CU(cudaStreamEndCapture(stream,&graph));CU(cudaGraphInstantiate(&exec,graph,0));
 CU(cudaGraphLaunch(exec,stream));CU(cudaStreamSynchronize(stream));CU(cudaMemcpy(got.data(),c,got.size()*2,cudaMemcpyDeviceToHost));
 double err=0,norm=0,max_abs=0;bool finite=true;
 for(size_t i=0;i<got.size();i++){double x=__bfloat162float(ref[i]),y=__bfloat162float(got[i]);finite&=std::isfinite(y);err+=(x-y)*(x-y);norm+=x*x;max_abs=std::max(max_abs,std::abs(x-y));}
 double rel=std::sqrt(err/std::max(norm,1e-30));assert(finite&&rel<.03);
 printf("seed=%d count=%zu rel_l2=%.12g max_abs=%.9g finite=%d graph=1\n",seed,got.size(),rel,max_abs,finite);fflush(stdout);
 CU(cudaGraphExecDestroy(exec));CU(cudaGraphDestroy(graph));
 }
 BL(cublasDestroy(h));CU(cudaFree(a));CU(cudaFree(b));CU(cudaFree(c));CU(cudaFree(ws));CU(cudaStreamDestroy(stream));
}
