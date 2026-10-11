#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cstdint>
using precision_t=__nv_bfloat16;
__device__ float to_float(precision_t x){return __bfloat162float(x);}
__device__ precision_t from_float(float x){return __float2bfloat16(x);}
constexpr int NH_MV=64,NH_CONCAT=1698;
__device__ __forceinline__ void nh_fxp_atomic_add(long long* addr,float v) {
 atomicAdd((unsigned long long*)addr,(unsigned long long)(long long)__float2ll_rn(v*16777216.0f));
}
__global__ void nh_min_dv_kernel(precision_t* __restrict__ dv,
    const precision_t* __restrict__ grad_concat, const float* __restrict__ amax,
    const float* __restrict__ vid, float eps, int n, int padv, int off, int B) {
    int64_t t = (int64_t)blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= (int64_t)B * n * NH_MV) return;
    int d = t % NH_MV;
    int k = (t / NH_MV) % n;
    int b = t / ((int64_t)n * NH_MV);
    float id = vid[(int64_t)b * n + k];
    int bad = padv >= 0 ? ((int)id == padv) : (id < 0.0f);
    const precision_t* gc = grad_concat + (int64_t)b * NH_CONCAT + off;
    float g = 0.0f;
    if (!bad) {
        g = eps * to_float(gc[d]);
        if ((int)amax[(int64_t)b * NH_MV + d] == k) g += to_float(gc[NH_MV + d]);
    }
    dv[t] = from_float(g);
}
__global__ void nh_relu_bias_bwd_kernel(
    precision_t* __restrict__ grad, const precision_t* __restrict__ out,
    long long* __restrict__ bias_acc, int64_t total, int dim) {
    extern __shared__ long long sdata[];
    for (int j = threadIdx.x; j < dim; j += blockDim.x) sdata[j] = 0;
    __syncthreads();
    int64_t i0 = (int64_t)blockIdx.x * blockDim.x + threadIdx.x;
    int64_t stride = (int64_t)gridDim.x * blockDim.x;
    float acc = 0.0f;
    for (int64_t i = i0; i < total; i += stride) {
        // branch-free: a divergent store-vs-load branch here runs ~3x slower
        float g = to_float(out[i]) > 0.0f ? to_float(grad[i]) : 0.0f;
        grad[i] = from_float(g);
        acc += g;
    }
    if (acc != 0.0f) nh_fxp_atomic_add(&sdata[(int)(i0 % dim)], acc);
    __syncthreads();
    for (int j = threadIdx.x; j < dim; j += blockDim.x)
        if (sdata[j] != 0) atomicAdd((unsigned long long*)&bias_acc[j], (unsigned long long)sdata[j]);
}
