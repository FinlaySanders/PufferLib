// ===== Stage B1 (14 Oct 2026): fused minGRU layer for inference (NH_MINGRU_FUSED=1): GEMM + gate in one launch =====
// combined[b, n] = sum_k x[b,k] * W[n,k] for the block's 96 columns (hidden/gate/proj of 32 hidden units), fp32 accumulation, rounded to
// bf16 exactly where the cuBLAS output was, then the rollout gate (same arithmetic as mingru_gate). out must not alias x (ping-pong buffers).
#define MF_ROWS 16
#define MF_HC 32
#define MF_KC 64
__global__ void __launch_bounds__(256) mingru_fused_layer(const precision_t* __restrict__ x, const precision_t* __restrict__ W,
        precision_t* __restrict__ state, precision_t* __restrict__ out, int H, int B) {
    __shared__ float xs[MF_ROWS][MF_KC];
    __shared__ float ws[3 * MF_HC][MF_KC + 1];
    __shared__ float cs[MF_ROWS][3 * MF_HC];
    int r0 = blockIdx.x * MF_ROWS, h0 = blockIdx.y * MF_HC, t = threadIdx.x;
    int row = t >> 4, cg = t & 15;
    float acc[6] = {0.f, 0.f, 0.f, 0.f, 0.f, 0.f};
    for (int k0 = 0; k0 < H; k0 += MF_KC) {
        for (int i = t; i < MF_ROWS * MF_KC; i += 256) {
            int r = i / MF_KC, k = i % MF_KC;
            xs[r][k] = (r0 + r < B) ? to_float(x[(long)(r0 + r) * H + k0 + k]) : 0.f;
        }
        for (int i = t; i < 3 * MF_HC * MF_KC; i += 256) {
            int c = i / MF_KC, k = i % MF_KC; int n = (c / MF_HC) * H + h0 + (c % MF_HC);
            ws[c][k] = to_float(W[(long)n * H + k0 + k]);
        }
        __syncthreads();
        #pragma unroll 8
        for (int k = 0; k < MF_KC; k++) {
            float xv = xs[row][k];
            #pragma unroll
            for (int c = 0; c < 6; c++) acc[c] += xv * ws[cg * 6 + c][k];
        }
        __syncthreads();
    }
    #pragma unroll
    for (int c = 0; c < 6; c++) cs[row][cg * 6 + c] = to_float(from_float(acc[c])); /* bf16 rounding point of the original combined buffer */
    __syncthreads();
    for (int p = t; p < MF_ROWS * MF_HC; p += 256) {
        int r = p / MF_HC, j = p % MF_HC;
        if (r0 + r >= B) continue;
        long idx = (long)(r0 + r) * H + h0 + j;
        float hidden = cs[r][j], gate = cs[r][MF_HC + j], proj = cs[r][2 * MF_HC + j];
        float st = to_float(state[idx]), xv = to_float(x[idx]);
        float z = sigmoid(gate);
        float h_tilde = (hidden >= 0.0f) ? hidden + 0.5f : sigmoid(hidden);
        float h_out = lerp(st, h_tilde, z);
        state[idx] = from_float(h_out);
        float s = sigmoid(proj);
        out[idx] = from_float(s * h_out + (1.0f - s) * xv);
    }
}
static int nh_mingru_fused = -1;
static bool mingru_fused_try(const precision_t* x, const precision_t* W, precision_t* state, precision_t* out, int B, int H, cudaStream_t stream) {
    if (nh_mingru_fused < 0) nh_mingru_fused = getenv("NH_MINGRU_FUSED") ? atoi(getenv("NH_MINGRU_FUSED")) : 0;
    if (!nh_mingru_fused || H % MF_HC || H % MF_KC || B > 1024 || x == out) return false;
    dim3 grid((B + MF_ROWS - 1) / MF_ROWS, H / MF_HC);
    mingru_fused_layer<<<grid, 256, 0, stream>>>(x, W, state, out, H, B);
    return true;
}
