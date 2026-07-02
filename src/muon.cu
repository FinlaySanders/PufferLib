#include <nccl.h>

__global__ void muon_norm_reduce(float* __restrict__ out, const float* __restrict__ partials, int num_blocks) {
    __shared__ float sdata[256];
    int tid = threadIdx.x;
    sdata[tid] = (tid < num_blocks) ? partials[tid] : 0.0f;
    __syncthreads();
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            sdata[tid] += sdata[tid + s];
        }
        __syncthreads();
    }
    if (tid == 0) {
        *out = sdata[0];
    }
}

__global__ void muon_norm_partials(float* __restrict__ partials, const precision_t* __restrict__ src, int n) {
    __shared__ float sdata[256];
    int tid = threadIdx.x;
    float sum = 0.0f;
    for (int i = blockIdx.x * blockDim.x + tid; i < n; i += blockDim.x * gridDim.x) {
        float v = to_float(src[i]);
        sum += v * v;
    }
    sdata[tid] = sum;
    __syncthreads();
    for (int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            sdata[tid] += sdata[tid + s];
        }
        __syncthreads();
    }
    if (tid == 0) {
        partials[blockIdx.x] = sdata[0];
    }
}

__global__ void muon_norm_apply(precision_t* __restrict__ dst, const float* __restrict__ norm_ptr, float eps, int n) {
    float inv_norm = 1.0f / fmaxf(sqrtf(*norm_ptr), eps);
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        dst[idx] = from_float(to_float(dst[idx]) * inv_norm);
    }
}

// Nesterov with f32 momentum accumulator and precision_t gradients
__global__ void muon_nesterov(float* __restrict__ mb, precision_t* __restrict__ gc, float mu, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        float m = mu * mb[idx] + to_float(gc[idx]);
        mb[idx] = m;
        gc[idx] = from_float(to_float(gc[idx]) + mu * m);
    }
}

// Fused weight update: wb = wb * (1 - lr*wd) - lr * scale * update
__global__ void muon_weight_update(float* __restrict__ wb, const precision_t* __restrict__ update,
        const float* __restrict__ lr_ptr, float wd, float scale, int n) {
    float lr = *lr_ptr;
    float wd_scale = 1.0f - lr * wd;
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        wb[idx] = wb[idx] * wd_scale - lr * scale * to_float(update[idx]);
    }
}

__global__ void muon_clip_norm(precision_t* __restrict__ dst,
        const float* __restrict__ sum_sq_ptr, float max_norm, float eps, int n) {
    float clip_coef = fminf(max_norm / (sqrtf(*sum_sq_ptr) + eps), 1.0f);
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        dst[idx] = from_float(to_float(dst[idx]) * clip_coef);
    }
}

static constexpr double ns_coeffs[5][3] = {
    {4.0848, -6.8946, 2.9270},
    {3.9505, -6.3029, 2.6377},
    {3.7418, -5.5913, 2.3037},
    {2.8769, -3.1427, 1.2046},
    {2.8366, -3.0525, 1.2012},
};

// Device copy of ns_coeffs — keep in sync with the table above.
__constant__ float ns_coeffs_dev[5][3] = {
    {4.0848f, -6.8946f, 2.9270f},
    {3.9505f, -6.3029f, 2.6377f},
    {3.7418f, -5.5913f, 2.3037f},
    {2.8769f, -3.1427f, 1.2046f},
    {2.8366f, -3.0525f, 1.2012f},
};

#define MUON_NS_THREADS 256
#define MUON_NS_MAX_PARAMS 64

// Metadata for the fused Newton-Schulz kernel. Passed by value at launch, so
// it gets baked into any capturing cudagraph — shapes and offsets are static.
struct MuonNSParams {
    long offset[MUON_NS_MAX_PARAMS];
    int rows[MUON_NS_MAX_PARAMS];
    int cols[MUON_NS_MAX_PARAMS];
    int count;
};

// Fused Newton-Schulz orthogonalization + weight update, one block per
// parameter. The cuBLAS loop below issues ~28 kernels per parameter; for the
// small matrices typical of these policies every one of them is dispatch
// overhead rather than math, and they serialize on the stream. This kernel
// does normalize + 5 NS iterations + the weight update in shared memory, and
// parameters run concurrently across blocks. Only parameters whose ping-pong
// iterates (2*R*C precision_t) plus gram matrices (2*M*M f32) fit in shared
// memory take this path (planned once in muon_init); larger ones keep cuBLAS.
// Gram/polynomial intermediates stay in f32 here, where the cuBLAS path
// rounds them to precision_t between GEMMs — bf16 builds differ in low bits.
__global__ void muon_ns_fused(
        float* __restrict__ wb, const precision_t* __restrict__ gc,
        const float* __restrict__ lr_ptr, float wd, MuonNSParams p) {
    extern __shared__ char muon_smem[];
    __shared__ float red[MUON_NS_THREADS];

    long offset = p.offset[blockIdx.x];
    int R = p.rows[blockIdx.x], C = p.cols[blockIdx.x];
    int M = min(R, C), N = max(R, C);
    bool tall = R > C;
    int RC = R * C;
    int tid = threadIdx.x;

    precision_t* X = (precision_t*)muon_smem;
    precision_t* X2 = X + RC;
    float* G = (float*)(X2 + RC);
    float* P = G + M * M;

    // Load and Frobenius-normalize: X = g / max(||g||_F, 1e-7)
    const precision_t* g_src = gc + offset;
    float ss = 0.0f;
    for (int i = tid; i < RC; i += MUON_NS_THREADS) {
        float v = to_float(g_src[i]);
        X[i] = from_float(v);
        ss += v * v;
    }
    red[tid] = ss;
    __syncthreads();
    for (int s = MUON_NS_THREADS / 2; s > 0; s >>= 1) {
        if (tid < s) {
            red[tid] += red[tid + s];
        }
        __syncthreads();
    }
    float inv_norm = 1.0f / fmaxf(sqrtf(red[0]), 1e-7f);
    for (int i = tid; i < RC; i += MUON_NS_THREADS) {
        X[i] = from_float(to_float(X[i]) * inv_norm);
    }
    __syncthreads();

    for (int it = 0; it < 5; ++it) {
        float a = ns_coeffs_dev[it][0];
        float b = ns_coeffs_dev[it][1];
        float c = ns_coeffs_dev[it][2];

        // G = X^T@X (tall) or X@X^T (wide), (M, M)
        for (int e = tid; e < M * M; e += MUON_NS_THREADS) {
            int i = e / M, j = e % M;
            float acc = 0.0f;
            if (tall) {
                for (int k = 0; k < N; ++k) {
                    acc += to_float(X[k * C + i]) * to_float(X[k * C + j]);
                }
            } else {
                for (int k = 0; k < N; ++k) {
                    acc += to_float(X[i * C + k]) * to_float(X[j * C + k]);
                }
            }
            G[e] = acc;
        }
        __syncthreads();

        // P = c*G@G + b*G
        for (int e = tid; e < M * M; e += MUON_NS_THREADS) {
            int i = e / M, j = e % M;
            float acc = 0.0f;
            for (int k = 0; k < M; ++k) {
                acc += G[i * M + k] * G[k * M + j];
            }
            P[e] = c * acc + b * G[e];
        }
        __syncthreads();

        // X' = X@P + a*X (tall) or P@X + a*X (wide)
        for (int e = tid; e < RC; e += MUON_NS_THREADS) {
            int i = e / C, j = e % C;
            float acc = 0.0f;
            if (tall) {
                for (int k = 0; k < M; ++k) {
                    acc += to_float(X[i * C + k]) * P[k * M + j];
                }
            } else {
                for (int k = 0; k < M; ++k) {
                    acc += P[i * M + k] * to_float(X[k * C + j]);
                }
            }
            X2[e] = from_float(acc + a * to_float(X[e]));
        }
        __syncthreads();

        precision_t* tmp = X; X = X2; X2 = tmp;
    }

    // Fused muon_weight_update: wb = wb*(1 - lr*wd) - lr*scale*update
    float lr = *lr_ptr;
    float wd_scale = 1.0f - lr * wd;
    float scale = sqrtf(fmaxf(1.0f, (float)R / (float)C));
    float* w_dst = wb + offset;
    for (int i = tid; i < RC; i += MUON_NS_THREADS) {
        w_dst[i] = w_dst[i] * wd_scale - lr * scale * to_float(X[i]);
    }
}

struct Muon {
    double momentum, weight_decay, eps;
    float lr_val_init;
    float* lr_ptr;
    float* lr_derived_ptr;
    float* norm_ptr;
    float* grad_norm_ptr;
    FloatTensor lr_puf, lr_derived_puf, ns_norm_puf, grad_norm_puf;
    FloatTensor mb_puf;
    PrecisionTensor gram, gram_buf, x_buf;
    FloatTensor norm_partials;
    long max_M, max_N;
    Allocator* param_alloc;  // params allocator — shapes used by muon_step
    ncclComm_t nccl_comm;
    int world_size;
    // Fused Newton-Schulz plan (see muon_ns_fused)
    MuonNSParams ns_params;
    size_t ns_fused_smem;
    bool* ns_fused;  // [param_alloc->num_regs] param handled by fused kernel
};

void muon_init(Muon* m, Allocator* param_alloc, double lr_val,
        double momentum, double eps, double weight_decay,
        Allocator* alloc) {
    m->momentum = momentum;
    m->weight_decay = weight_decay;
    m->eps = eps;
    m->lr_val_init = (float)lr_val;
    m->lr_ptr = nullptr;
    m->lr_derived_ptr = nullptr;
    m->param_alloc = param_alloc;
    m->nccl_comm = nullptr;
    m->world_size = 1;
    m->max_M = 0; m->max_N = 0;
    long n = param_alloc->total_elems;
    m->lr_puf =         {.shape = {1}};
    m->lr_derived_puf = {.shape = {2}};
    m->mb_puf =         {.shape = {n}};
    m->norm_partials =  {.shape = {256}};
    m->grad_norm_puf =  {.shape = {1}};
    alloc_register(alloc, &m->lr_puf);
    alloc_register(alloc, &m->lr_derived_puf);
    alloc_register(alloc, &m->mb_puf);
    alloc_register(alloc, &m->norm_partials);
    alloc_register(alloc, &m->grad_norm_puf);
    long max_M = 0, max_N = 0;
    for (int _i = 0; _i < param_alloc->num_regs; _i++) {
        AllocEntry& e = param_alloc->regs[_i];
        if (ndim(e.shape) >= 2) {
            long R = e.shape[0], C = numel(e.shape) / R;
            max_M = max(max_M, min(R, C));
            max_N = max(max_N, max(R, C));
        }
    }
    if (max_M > 0) {
        m->max_M = max_M; m->max_N = max_N;
        m->gram =        {.shape = {max_M, max_M}};
        m->gram_buf =    {.shape = {max_M, max_M}};
        m->x_buf =       {.shape = {max_M, max_N}};
        m->ns_norm_puf = {.shape = {1}};
        alloc_register(alloc, &m->gram);
        alloc_register(alloc, &m->gram_buf);
        alloc_register(alloc, &m->x_buf);
        alloc_register(alloc, &m->ns_norm_puf);
    }

    // Plan the fused Newton-Schulz path from static shapes: 2D params whose
    // shared-memory footprint fits the device get one muon_ns_fused block
    // each; the rest stay on the cuBLAS loop in muon_step. Decided once here
    // so cudagraph capture and replay always agree.
    m->ns_params.count = 0;
    m->ns_fused_smem = 0;
    m->ns_fused = (bool*)calloc(param_alloc->num_regs, sizeof(bool));
    int device = 0, smem_max = 0;
    cudaGetDevice(&device);
    cudaDeviceGetAttribute(&smem_max, cudaDevAttrMaxSharedMemoryPerBlockOptin, device);
    long off = 0;
    for (int _i = 0; _i < param_alloc->num_regs; _i++) {
        AllocEntry& e = param_alloc->regs[_i];
        long ne = numel(e.shape);
        if (ndim(e.shape) >= 2 && m->ns_params.count < MUON_NS_MAX_PARAMS) {
            long R = e.shape[0], C = ne / R;
            long M = min(R, C);
            size_t smem = 2 * ne * sizeof(precision_t) + 2 * M * M * sizeof(float);
            // 2KB headroom for the kernel's static shared reduction buffer
            if (smem + 2048 <= (size_t)smem_max) {
                int idx = m->ns_params.count++;
                m->ns_params.offset[idx] = off;
                m->ns_params.rows[idx] = (int)R;
                m->ns_params.cols[idx] = (int)C;
                m->ns_fused[_i] = true;
                if (smem > m->ns_fused_smem) m->ns_fused_smem = smem;
            }
        }
        off += ne;
    }
    if (m->ns_fused_smem > 48 * 1024) {
        cudaFuncSetAttribute(muon_ns_fused,
            cudaFuncAttributeMaxDynamicSharedMemorySize, (int)m->ns_fused_smem);
    }
}

void muon_post_create(Muon* m) {
    m->lr_ptr = m->lr_puf.data;
    m->lr_derived_ptr = m->lr_derived_puf.data;
    m->grad_norm_ptr = m->grad_norm_puf.data;
    if (m->ns_norm_puf.data) m->norm_ptr = m->ns_norm_puf.data;
    cudaMemcpy(m->lr_ptr, &m->lr_val_init, sizeof(float), cudaMemcpyHostToDevice);
    cudaMemset(m->lr_derived_ptr, 0, 2 * sizeof(float));
    cudaMemset(m->mb_puf.data, 0, numel(m->mb_puf.shape) * sizeof(float));
}

void muon_step(Muon* m, FloatTensor weights, PrecisionTensor grads, float max_grad_norm, cudaStream_t stream = 0) {
    // Multi-GPU support: simple all-reduce over a contiguous grad buffer
    if (m->nccl_comm != nullptr && m->world_size > 1) {
        ncclAllReduce(grads.data, grads.data, numel(grads.shape),
            NCCL_PRECISION, ncclAvg, m->nccl_comm, stream);
    }

    // Clip gradients by norm
    int clip_blocks = min((int)grid_size(numel(grads.shape)), 256);
    muon_norm_partials<<<clip_blocks, 256, 0, stream>>>(
        m->norm_partials.data, grads.data, numel(grads.shape));
    muon_norm_reduce<<<1, 256, 0, stream>>>(m->grad_norm_ptr, m->norm_partials.data, clip_blocks);
    muon_clip_norm<<<grid_size(numel(grads.shape)), BLOCK_SIZE, 0, stream>>>(
        grads.data, m->grad_norm_ptr, max_grad_norm, 1e-6f, numel(grads.shape));

    // Nesterov momentum
    muon_nesterov<<<grid_size(numel(m->mb_puf.shape)), BLOCK_SIZE, 0, stream>>>(
        m->mb_puf.data, grads.data, (float)m->momentum, numel(m->mb_puf.shape));

    // Fused Newton-Schulz for small params: one block per param replaces the
    // per-param norm/GEMM/copy chain and weight update in the loop below.
    if (m->ns_params.count > 0) {
        muon_ns_fused<<<m->ns_params.count, MUON_NS_THREADS, m->ns_fused_smem, stream>>>(
            weights.data, grads.data, m->lr_ptr, (float)m->weight_decay, m->ns_params);
    }

    long offset = 0;
    for (int _i = 0; _i < m->param_alloc->num_regs; _i++) {
        AllocEntry& e = m->param_alloc->regs[_i];
        long ne = numel(e.shape);
        if (m->ns_fused[_i]) {
            offset += ne;  // handled by muon_ns_fused (incl. weight update)
            continue;
        }
        precision_t* gc_ptr = grads.data + offset;
        float* wb_ptr = weights.data + offset;
        const precision_t* update_ptr = gc_ptr;
        float scale = 1.0f;

        // Orthogonalize the update
        if (ndim(e.shape) >= 2) {
            long R = e.shape[0], C = ne / R;
            long M = min(R, C), N = max(R, C);
            bool tall = R > C;
            PrecisionTensor x = {.data = gc_ptr, .shape = {R, C}};
            PrecisionTensor x_buf = {.data = m->x_buf.data, .shape = {R, C}};
            PrecisionTensor gram = {.data = m->gram.data, .shape = {M, M}};
            PrecisionTensor gram_buf = {.data = m->gram_buf.data, .shape = {M, M}};

            int nblk = min((int)grid_size(numel(x.shape)), 256);
            muon_norm_partials<<<nblk, 256, 0, stream>>>(
                m->norm_partials.data, x.data, numel(x.shape));
            muon_norm_reduce<<<1, 256, 0, stream>>>(m->norm_ptr, m->norm_partials.data, nblk);
            muon_norm_apply<<<grid_size(numel(x.shape)), BLOCK_SIZE, 0, stream>>>(
                x.data, m->norm_ptr, 1e-7f, numel(x.shape));

            cublasOperation_t gram_op_a = tall ? CUBLAS_OP_T : CUBLAS_OP_N;
            cublasOperation_t gram_op_b = tall ? CUBLAS_OP_N : CUBLAS_OP_T;
            for (int i = 0; i < 5; ++i) {
                PrecisionTensor& src = (i % 2 == 0) ? x : x_buf;
                PrecisionTensor& dst = (i % 2 == 0) ? x_buf : x;
                cublasGemmExDense(gram_op_a, gram_op_b, (int)M, (int)M, (int)N,
                    src.data, src.data, gram.data, stream);
                puf_copy(&gram_buf, &gram, stream);
                puf_addmm_nn(&gram, &gram, &gram_buf, ns_coeffs[i][2], ns_coeffs[i][1], stream);
                puf_copy(&dst, &src, stream);
                cublasGemmExDense(CUBLAS_OP_N, CUBLAS_OP_N, (int)R, (int)C, (int)M,
                    tall ? src.data : gram_buf.data, tall ? gram_buf.data : src.data, dst.data,
                    stream, 1.0f, ns_coeffs[i][0]);
            }

            update_ptr = x_buf.data;
            scale = sqrtf(fmaxf(1.0f, (float)R / (float)C));
        }

        muon_weight_update<<<grid_size(ne), BLOCK_SIZE, 0, stream>>>(
            wb_ptr, update_ptr, m->lr_ptr, (float)m->weight_decay, scale, (int)ne);
        offset += ne;
    }
}
