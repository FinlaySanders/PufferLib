#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublas_v2.h>
#include <cassert>
using precision_t=__nv_bfloat16;
__device__ float to_float(precision_t x){return __bfloat162float(x);}
__device__ precision_t from_float(float x){return __float2bfloat16(x);}
__device__ __forceinline__ float sigmoid(float x) {
    float z = expf(-fabsf(x));
    return x >= 0.0f ? 1.0f / (1.0f + z) : z / (1.0f + z);
}

__device__ __forceinline__ float lerp(float a, float b, float w) {
    float diff = b - a;
    return (fabsf(w) < 0.5f) ? a + w * diff : b - diff * (1.0f - w);
}

// Rollout MinGRU step: h = (1-z)*h + z*h_tilde, highway out = s*h + (1-s)*x.
__global__ void mingru_gate(precision_t* out, precision_t* next_state,
        const precision_t* combined, const precision_t* state_in,
        const precision_t* x_in, int H, int B) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    int N = B * H;
    if (idx >= N) {
        return;
    }

    int b = idx / H;
    int h = idx % H;

    int combined_base = b * 3 * H;
    float hidden = to_float(combined[combined_base + h]);
    float gate = to_float(combined[combined_base + H + h]);
    float proj = to_float(combined[combined_base + 2*H + h]);
    float state = to_float(state_in[idx]);
    float x = to_float(x_in[idx]);

    float z = sigmoid(gate);
    float h_tilde = (hidden >= 0.0f) ? hidden + 0.5f : sigmoid(hidden);
    float h_out = lerp(state, h_tilde, z);
    next_state[idx] = from_float(h_out);

    float s = sigmoid(proj);
    out[idx] = from_float(s * h_out + (1.0f - s) * x);
}


static cublasHandle_t handle;
static void* workspace;
static cudaStream_t rec_stream;
extern "C" void rec_init(void* stream) {
 rec_stream=(cudaStream_t)stream;
 assert(cublasCreate(&handle)==CUBLAS_STATUS_SUCCESS);
 assert(cublasSetStream(handle,rec_stream)==CUBLAS_STATUS_SUCCESS);
 assert(cudaMalloc(&workspace,4u<<20)==cudaSuccess);
 assert(cublasSetWorkspace(handle,workspace,4u<<20)==CUBLAS_STATUS_SUCCESS);
 assert(cublasSetMathMode(handle,CUBLAS_DEFAULT_MATH)==CUBLAS_STATUS_SUCCESS);
}
extern "C" void rec_run(void* x,void* w,void* c,void* h,void* out,void* next,int m,int n) {
 float a=1,b=0;
 assert(cublasGemmEx(handle,CUBLAS_OP_T,CUBLAS_OP_N,3*n,m,n,&a,w,CUDA_R_16BF,n,x,CUDA_R_16BF,n,&b,c,CUDA_R_16BF,3*n,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT)==CUBLAS_STATUS_SUCCESS);
 mingru_gate<<<(m*n+255)/256,256,0,rec_stream>>>((precision_t*)out,(precision_t*)next,(precision_t*)c,(precision_t*)h,(precision_t*)x,n,m);
 assert(cudaPeekAtLastError()==cudaSuccess);
}
