// Isolated deterministic tree reductions; same FP32 accumulation type.
// A warp owns one sample so the 40 identity features are written contiguously.
__global__ void nh_idemb_warp_kernel(precision_t* __restrict__ concat,
    float* __restrict__ idx_out, const nh_obs_t* __restrict__ obs,
    const precision_t* __restrict__ role_w, const precision_t* __restrict__ race_w,
    const precision_t* __restrict__ gend_w, const precision_t* __restrict__ algn_w, int B) {
    int thread = blockIdx.x * blockDim.x + threadIdx.x;
    int b = thread / 32, lane = thread & 31;
    if (b >= B) return;
    int r = 0, rc = 0, g = 0, al = 0;
    if (lane == 0) {
        const nh_obs_t* bl = obs + (int64_t)b * NH_OBS_SIZE + NH_BL_OFF;
        const nh_obs_t* ex = bl + 4 * NH_BL_RAW;
        for (int i = 0; i < 13; i++) if (nh_bl_read_i32(ex + 4 * (NH_EX_ROLEOH + i))) r = i;
        for (int i = 0; i < 5; i++) if (nh_bl_read_i32(ex + 4 * (NH_EX_ROLEOH + 13 + i))) rc = i;
        for (int i = 0; i < 2; i++) if (nh_bl_read_i32(ex + 4 * (NH_EX_ROLEOH + 18 + i))) g = i;
        al = 1 - nh_bl_read_i32(bl + 4 * 26);
        al = al < 0 ? 0 : al > 2 ? 2 : al;
        idx_out[b * 4 + 0] = (float)r;
        idx_out[b * 4 + 1] = (float)rc;
        idx_out[b * 4 + 2] = (float)g;
        idx_out[b * 4 + 3] = (float)al;
    }
    r = __shfl_sync(0xffffffff, r, 0);
    rc = __shfl_sync(0xffffffff, rc, 0);
    g = __shfl_sync(0xffffffff, g, 0);
    al = __shfl_sync(0xffffffff, al, 0);
    precision_t* c = concat + (int64_t)b * NH_CONCAT + NH_IDE_CONCAT_OFF;
    for (int d = lane; d < NH_IDE_DIM; d += 32) {
        if (d < NH_IDE_ROLE) c[d] = role_w[r * NH_IDE_ROLE + d];
        else if (d < NH_IDE_ROLE + NH_IDE_RACE)
            c[d] = race_w[rc * NH_IDE_RACE + d - NH_IDE_ROLE];
        else if (d < NH_IDE_ROLE + NH_IDE_RACE + NH_IDE_GEND)
            c[d] = gend_w[g * NH_IDE_GEND + d - NH_IDE_ROLE - NH_IDE_RACE];
        else c[d] = algn_w[al * NH_IDE_ALGN + d - NH_IDE_ROLE - NH_IDE_RACE - NH_IDE_GEND];
    }
}

__device__ __forceinline__ float nh_embed_block_sum(float value) {
    __shared__ float partials[8];
    int lane = threadIdx.x & 31, warp = threadIdx.x >> 5;
    for (int shift = 16; shift; shift >>= 1)
        value += __shfl_down_sync(0xffffffff, value, shift);
    if (lane == 0) partials[warp] = value;
    __syncthreads();
    if (warp == 0) {
        value = lane < 8 ? partials[lane] : 0.0f;
        for (int shift = 16; shift; shift >>= 1)
            value += __shfl_down_sync(0xffffffff, value, shift);
    }
    return value;
}
static int nh_embed_reduce_bits() {
    const char* value = getenv("NH_EMBED_REDUCE");
    return value ? atoi(value) : 0;
}
__global__ void nh_idemb_grad_parallel_kernel(precision_t* __restrict__ role_g,
    precision_t* __restrict__ race_g, precision_t* __restrict__ gend_g,
    precision_t* __restrict__ algn_g, const precision_t* __restrict__ grad_concat,
    const float* __restrict__ idx, int B) {
    int t = blockIdx.x;
    const int n_role = 13 * NH_IDE_ROLE, n_race = 5 * NH_IDE_RACE;
    const int n_gend = 2 * NH_IDE_GEND, n_algn = 3 * NH_IDE_ALGN;
    if (t >= n_role + n_race + n_gend + n_algn) return;
    int comp, wdt, off;
    precision_t* out;
    int u = t;
    if (u < n_role) { comp = 0; wdt = NH_IDE_ROLE; off = 0; out = role_g; }
    else if ((u -= n_role) < n_race) { comp = 1; wdt = NH_IDE_RACE; off = NH_IDE_ROLE; out = race_g; }
    else if ((u -= n_race) < n_gend) { comp = 2; wdt = NH_IDE_GEND; off = NH_IDE_ROLE + NH_IDE_RACE; out = gend_g; }
    else { u -= n_gend; comp = 3; wdt = NH_IDE_ALGN; off = NH_IDE_ROLE + NH_IDE_RACE + NH_IDE_GEND; out = algn_g; }
    int row = u / wdt, d = u % wdt;
    float acc = 0.0f;
    for (int b = threadIdx.x; b < B; b += blockDim.x) {
        if ((int)idx[b * 4 + comp] != row) continue;
        acc += to_float(grad_concat[(int64_t)b * NH_CONCAT + NH_IDE_CONCAT_OFF + off + d]);
    }
    acc = nh_embed_block_sum(acc);
    if (threadIdx.x == 0) out[row * wdt + d] = from_float(acc);
}
__global__ void nh_ekind_grad_parallel_kernel(precision_t* __restrict__ dK,
    const precision_t* __restrict__ dE) {
    int i = blockIdx.x;
    if (i >= NH_NKIND * NH_EMBED_DIM) return;
    int r = i / NH_EMBED_DIM, d = i % NH_EMBED_DIM;
    float acc = 0.0f;
    for (int j = nh_kind_csr_off[r] + threadIdx.x; j < nh_kind_csr_off[r + 1]; j += blockDim.x)
        acc += to_float(dE[(int64_t)nh_kind_csr_glyph[j] * NH_EMBED_DIM + d]);
    acc = nh_embed_block_sum(acc);
    if (threadIdx.x == 0) dK[i] = from_float(acc);
}

// Fixed-point conversion occurs before reduction, preserving integer sums.
__global__ void nh_loc3_scatter_shared_kernel(long long* __restrict__ acc,
    const precision_t* __restrict__ dx, const float* __restrict__ crop_glyph,
    const unsigned char* __restrict__ lut, int B) {
    __shared__ unsigned long long bins[NH_LOCC_CLASSES * NH_LOCC_DIM];
    for (int i = threadIdx.x; i < NH_LOCC_CLASSES * NH_LOCC_DIM; i += blockDim.x)
        bins[i] = 0;
    __syncthreads();
    for (int t = blockIdx.x * blockDim.x + threadIdx.x;
            t < B * NH_LOC_IN; t += gridDim.x * blockDim.x) {
        int b = t / NH_LOC_IN, j = t % NH_LOC_IN;
        int p = j / NH_LOCC_DIM, d = j % NH_LOCC_DIM;
        int g = (int)crop_glyph[(int64_t)b * NH_CGRID + p];
        int cls = p == (NH_CGRID / 2) ? 7 : (int)lut[g];
        float v = to_float(dx[t]);
        if (v != 0.0f) atomicAdd(&bins[cls * NH_LOCC_DIM + d],
            (unsigned long long)(long long)__float2ll_rn(v * NH_FXP));
    }
    __syncthreads();
    for (int i = threadIdx.x; i < NH_LOCC_CLASSES * NH_LOCC_DIM; i += blockDim.x)
        if (bins[i]) atomicAdd((unsigned long long*)&acc[i], bins[i]);
}
