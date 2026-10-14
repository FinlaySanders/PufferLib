template<int N, int PAD, int OFF>
__device__ __forceinline__ float pool_gradient(int64_t t,
        const precision_t* grad_concat, const float* amax,
        const float* vid, float eps) {
    int d = t % 64;
    int k = (t / 64) % N;
    int b = t / ((int64_t)N * 64);
    float id = vid[(int64_t)b * N + k];
    int bad = PAD >= 0 ? ((int)id == PAD) : (id < 0.0f);
    const precision_t* gc = grad_concat + (int64_t)b * NH_CONCAT + OFF;
    float g = 0.0f;
    if (!bad) {
        g = eps * to_float(gc[d]);
        if ((int)amax[(int64_t)b * 64 + d] == k)
            g += to_float(gc[64 + d]);
    }
    return to_float(from_float(g));
}

template<int N, int PAD, int OFF>
__global__ void pool_dv_specialized(precision_t* dv,
        const precision_t* grad_concat, const float* amax,
        const float* vid, float eps, int B) {
    int64_t t = (int64_t)blockIdx.x * blockDim.x + threadIdx.x;
    if (t < (int64_t)B * N * 64)
        dv[t] = from_float((pool_gradient<N, PAD, OFF>(t, grad_concat, amax, vid, eps)));
}

template<int N, int PAD, int OFF>
__global__ void pool_dv_relu_bias(precision_t* dv,
        const precision_t* grad_concat, const float* amax,
        const float* vid, float eps, int B,
        const precision_t* out, long long* bias_acc) {
    extern __shared__ long long sdata[];
    for (int j = threadIdx.x; j < 64; j += blockDim.x) sdata[j] = 0;
    __syncthreads();
    int64_t i0 = (int64_t)blockIdx.x * blockDim.x + threadIdx.x;
    int64_t stride = (int64_t)gridDim.x * blockDim.x;
    float acc = 0.0f;
    for (int64_t i = i0; i < (int64_t)B * N * 64; i += stride) {
        float rounded = pool_gradient<N, PAD, OFF>(i, grad_concat, amax, vid, eps);
        float g = to_float(out[i]) > 0.0f ? rounded : 0.0f;
        dv[i] = from_float(g);
        acc += g;
    }
    if (acc != 0.0f) nh_fxp_atomic_add(&sdata[(int)(i0 % 64)], acc);
    __syncthreads();
    for (int j = threadIdx.x; j < 64; j += blockDim.x)
        if (sdata[j] != 0)
            atomicAdd((unsigned long long*)&bias_acc[j], (unsigned long long)sdata[j]);
}
