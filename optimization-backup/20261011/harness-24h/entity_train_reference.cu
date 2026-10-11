#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublasLt.h>
#include <cublas_v2.h>
#include <cassert>
#include <cstdint>
using precision_t=__nv_bfloat16;
__device__ float to_float(precision_t x){return __bfloat162float(x);}
__device__ precision_t from_float(float x){return __float2bfloat16(x);}
constexpr int NH_MV=64,NH_CONCAT=1698;
__global__ void nh_min_summax_kernel(precision_t* __restrict__ concat,
    float* __restrict__ amax, const precision_t* __restrict__ v,
    const float* __restrict__ vid, float eps, int n, int padv, int off, int B) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= B * NH_MV) return;
    int b = t / NH_MV, d = t % NH_MV;
    float sm = 0.0f, mx = -1e30f;
    int bm = -1;
    for (int k = 0; k < n; k++) {
        float id = vid[(int64_t)b * n + k];
        int bad = padv >= 0 ? ((int)id == padv) : (id < 0.0f);
        if (bad) continue;
        float vv = to_float(v[((int64_t)b * n + k) * NH_MV + d]);
        sm += vv;
        if (vv > mx) { mx = vv; bm = k; }
    }
    amax[t] = (float)bm;
    precision_t* dst = concat + (int64_t)b * NH_CONCAT + off;
    dst[d] = from_float(sm * eps);
    dst[NH_MV + d] = from_float(bm >= 0 ? mx : 0.0f);
}

static cublasHandle_t handle;
static void* workspace;
static cudaStream_t stream;
static int gn,go,gp,gbatch;static float ge;
static void *gb1,*gb2;
__global__ void relu_bias(precision_t* x,const precision_t* bias,int n) {
 int t=blockIdx.x*blockDim.x+threadIdx.x;
 if(t<n) x[t]=from_float(fmaxf(0.0f,to_float(x[t])+to_float(bias[t%64])));
}
extern "C" void inv_init(void* st,void* b1,void* b2,int batch,int n,int off,int pad,float eps) {
 stream=(cudaStream_t)st;gn=n;go=off;gp=pad;ge=eps;gbatch=batch;gb1=b1;gb2=b2;
 assert(cublasCreate(&handle)==CUBLAS_STATUS_SUCCESS);
 assert(cublasSetStream(handle,stream)==CUBLAS_STATUS_SUCCESS);
 assert(cudaMalloc(&workspace,4u<<20)==cudaSuccess);
 assert(cublasSetWorkspace(handle,workspace,4u<<20)==CUBLAS_STATUS_SUCCESS);
 assert(cublasSetMathMode(handle,CUBLAS_DEFAULT_MATH)==CUBLAS_STATUS_SUCCESS);
}
static void mm(int k,void* x,void* w,void* y,void* bias) {
 float alpha=1,beta=0;
 assert(cublasGemmEx(handle,CUBLAS_OP_T,CUBLAS_OP_N,64,gbatch*gn,k,&alpha,w,CUDA_R_16BF,k,x,CUDA_R_16BF,k,&beta,y,CUDA_R_16BF,64,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT)==CUBLAS_STATUS_SUCCESS);
 relu_bias<<<(gbatch*gn*64+255)/256,256,0,stream>>>((precision_t*)y,(precision_t*)bias,gbatch*gn*64);
}
extern "C" void inv_run(void* x,void* w1,void* w2,void* h,void* v,void* gid,void* concat,void* amax,int batch) {
 mm(16,x,w1,h,gb1);mm(64,h,w2,v,gb2);
 nh_min_summax_kernel<<<(batch*64+255)/256,256,0,stream>>>((precision_t*)concat,(float*)amax,(precision_t*)v,(float*)gid,ge,gn,gp,go,batch);
 assert(cudaPeekAtLastError()==cudaSuccess);
}
