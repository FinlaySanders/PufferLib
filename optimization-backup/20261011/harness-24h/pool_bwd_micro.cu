#include "pool_bwd_reference_parts.cu"
#include "pool_bwd_candidate.cuh"

template<int N, int PAD, int OFF>
static void launch(int mode, precision_t* dv, const precision_t* gc,
        const float* am, const float* gid, const precision_t* out,
        long long* bias, int B, float eps, cudaStream_t stream) {
    int64_t total = (int64_t)B * N * 64;
    int grid = (total + 255) / 256;
    int bias_grid = grid > 1024 ? 1024 : grid;
    assert(cudaMemsetAsync(bias, 0, 64 * sizeof(long long), stream) == cudaSuccess);
    if (mode == 0) {
        nh_min_dv_kernel<<<grid, 256, 0, stream>>>(dv, gc, am, gid, eps, N, PAD, OFF, B);
    } else if (mode == 1) {
        pool_dv_specialized<N, PAD, OFF><<<grid, 256, 0, stream>>>(dv, gc, am, gid, eps, B);
    } else {
        pool_dv_relu_bias<N, PAD, OFF><<<bias_grid, 256, 64 * sizeof(long long), stream>>>(
            dv, gc, am, gid, eps, B, out, bias);
    }
    if (mode < 2)
        nh_relu_bias_bwd_kernel<<<bias_grid, 256, 64 * sizeof(long long), stream>>>(dv, out, bias, total, 64);
    assert(cudaPeekAtLastError() == cudaSuccess);
}

extern "C" void pool_run(int mode, int branch, void* dv, void* gc,
        void* am, void* gid, void* out, void* bias, int B, void* stream) {
#define ARGS mode,(precision_t*)dv,(precision_t*)gc,(float*)am,(float*)gid,(precision_t*)out,(long long*)bias,B
    if (branch == 0) launch<55, 5976, 1010>(ARGS, .2f, (cudaStream_t)stream);
    if (branch == 1) launch<16, -1, 1394>(ARGS, .25f, (cudaStream_t)stream);
    if (branch == 2) launch<16, -1, 1538>(ARGS, .25f, (cudaStream_t)stream);
    if (branch == 3) launch<8, -1, 838>(ARGS, .25f, (cudaStream_t)stream);
#undef ARGS
}
