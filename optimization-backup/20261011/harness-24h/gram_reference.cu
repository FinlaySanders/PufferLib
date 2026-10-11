#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <cassert>
static cublasHandle_t handle;
static void* workspace;
extern "C" void gram_init(void* stream) {
 assert(cublasCreate(&handle)==CUBLAS_STATUS_SUCCESS);
 assert(cublasSetStream(handle,(cudaStream_t)stream)==CUBLAS_STATUS_SUCCESS);
 assert(cudaMalloc(&workspace,4u<<20)==cudaSuccess);
 assert(cublasSetWorkspace(handle,workspace,4u<<20)==CUBLAS_STATUS_SUCCESS);
 assert(cublasSetMathMode(handle,CUBLAS_DEFAULT_MATH)==CUBLAS_STATUS_SUCCESS);
}
extern "C" void gram_run(void* x,void* out,int n,int k) {
 float a=1,b=0;
 assert(cublasGemmEx(handle,CUBLAS_OP_N,CUBLAS_OP_T,n,n,k,&a,x,CUDA_R_16BF,n,x,CUDA_R_16BF,n,&b,out,CUDA_R_16BF,n,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT)==CUBLAS_STATUS_SUCCESS);
}
