"""Stage B2: latency-oriented small GEMM (bias/ReLU epilogue, fp32 accumulate, bf16 in/out) replacing cuBLASLt for the inference encoder
matmuls and the decoder (NH_GEMM_FUSED=1); padded scheduler rows are skipped by every fused inference kernel (row-valid cutoff)."""
from pathlib import Path
A=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/algo.cu'); t=A.read_text()
def rep(old,new,count=1):
    global t; assert t.count(old)==count, (t.count(old), old[:90]); t=t.replace(old,new)
rep("""Prec decoder_forward(void* w, void* activations, Prec input, cudaStream_t stream) {""",
"""// ===== Stage B2 (14 Oct 2026): small GEMM for inference rows (NH_GEMM_FUSED=1) =====
// out[m,n] = relu?(sum_k A[m,k] W[n,k] + bias[n]); one launch per matmul, blocks whose first row is a padded scheduler row exit at once.
thread_local const int* g_row_valid = NULL; thread_local int g_row_valid_rows = 0; thread_local bool g_small_gemm_infer = false;
static int nh_gemm_fused_env() { static int v = -1; if (v < 0) v = getenv("NH_GEMM_FUSED") ? atoi(getenv("NH_GEMM_FUSED")) : 0; return v; }
#define SG_BM 16
#define SG_BN 64
#define SG_BK 64
__global__ void __launch_bounds__(256) small_gemm_kernel(const precision_t* __restrict__ A, const precision_t* __restrict__ W,
        precision_t* __restrict__ O, const precision_t* __restrict__ bias, int relu, int M, int N, int K, const int* __restrict__ row_valid) {
    int m0 = blockIdx.x * SG_BM, n0 = blockIdx.y * SG_BN;
    if (row_valid && row_valid[m0] < 0) return;
    __shared__ float As[SG_BM][SG_BK + 1];
    __shared__ float Ws[SG_BN][SG_BK + 1];
    int t = threadIdx.x, row = t >> 4, cq = t & 15;
    float acc[4] = {0.f, 0.f, 0.f, 0.f};
    for (int k0 = 0; k0 < K; k0 += SG_BK) {
        for (int i = t; i < SG_BM * SG_BK; i += 256) { int r = i / SG_BK, k = i % SG_BK; int gm = m0 + r, gk = k0 + k;
            As[r][k] = (gm < M && gk < K) ? to_float(A[(long)gm * K + gk]) : 0.f; }
        for (int i = t; i < SG_BN * SG_BK; i += 256) { int c = i / SG_BK, k = i % SG_BK; int gn = n0 + c, gk = k0 + k;
            Ws[c][k] = (gn < N && gk < K) ? to_float(W[(long)gn * K + gk]) : 0.f; }
        __syncthreads();
        #pragma unroll 8
        for (int k = 0; k < SG_BK; k++) {
            float a = As[row][k];
            acc[0] += a * Ws[cq][k]; acc[1] += a * Ws[cq + 16][k]; acc[2] += a * Ws[cq + 32][k]; acc[3] += a * Ws[cq + 48][k];
        }
        __syncthreads();
    }
    int gm = m0 + row;
    if (gm >= M) return;
    #pragma unroll
    for (int c = 0; c < 4; c++) {
        int gn = n0 + cq + 16 * c;
        if (gn >= N) continue;
        float v = acc[c] + (bias ? to_float(bias[gn]) : 0.f);
        if (relu) v = v > 0.f ? v : 0.f;
        O[(long)gm * N + gn] = from_float(v);
    }
}
static bool nh_small_mm_raw(const precision_t* A, const precision_t* W, precision_t* O, const precision_t* bias, int relu, int M, int N, int K, cudaStream_t stream) {
    if (!nh_gemm_fused_env() || !g_small_gemm_infer || M <= 0 || N <= 0 || K <= 0) return false;
    const int* rv = (g_row_valid && M == g_row_valid_rows) ? g_row_valid : NULL;
    dim3 grid((M + SG_BM - 1) / SG_BM, (N + SG_BN - 1) / SG_BN);
    small_gemm_kernel<<<grid, 256, 0, stream>>>(A, W, O, bias, relu, M, N, K, rv);
    return true;
}
// Same operand convention as puf_mm: out(M,N) = a(M,K) @ b(N,K)^T (+ bias[N]) (relu)
static bool nh_small_mm(Prec* a, Prec* b, Prec* out, const precision_t* bias, int relu, cudaStream_t stream) {
    int M = batch_size(a->shape) * a->shape[ndim(a->shape)-2];
    int K = a->shape[ndim(a->shape)-1];
    int N = b->shape[ndim(b->shape)-2];
    return nh_small_mm_raw(a->data, b->data, out->data, bias, relu, M, N, K, stream);
}
Prec decoder_forward(void* w, void* activations, Prec input, cudaStream_t stream) {""")
rep("""    if (a->saved_input.data) {
        puf_copy(&a->saved_input, &input, stream);
    }
    puf_mm(&input, &dw->weight, &a->out, stream);
    return a->out;""",
"""    if (a->saved_input.data) {
        puf_copy(&a->saved_input, &input, stream);
    }
    if (!a->saved_input.data && nh_small_mm(&input, &dw->weight, &a->out, NULL, 0, stream)) return a->out;
    puf_mm(&input, &dw->weight, &a->out, stream);
    return a->out;""")
# minGRU fused: row cutoff
rep("""    if (!nh_mingru_fused || H % MF_HC || H % MF_KC || B > 1024 || x == out) return false;
    dim3 grid((B + MF_ROWS - 1) / MF_ROWS, H / MF_HC);
    mingru_fused_layer<<<grid, 256, 0, stream>>>(x, W, state, out, H, B);""",
"""    if (!nh_mingru_fused || H % MF_HC || H % MF_KC || B > 1024 || x == out) return false;
    dim3 grid((B + MF_ROWS - 1) / MF_ROWS, H / MF_HC);
    const int* rv = (g_row_valid && B == g_row_valid_rows) ? g_row_valid : NULL;
    mingru_fused_layer<<<grid, 256, 0, stream>>>(x, W, state, out, H, B, rv);""")
rep("""        precision_t* __restrict__ state, precision_t* __restrict__ out, int H, int B) {
    __shared__ float xs[MF_ROWS][MF_KC];""",
"""        precision_t* __restrict__ state, precision_t* __restrict__ out, int H, int B, const int* __restrict__ row_valid) {
    if (row_valid && row_valid[blockIdx.x * MF_ROWS] < 0) return;
    __shared__ float xs[MF_ROWS][MF_KC];""")
A.write_text(t)
N=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/ocean/nethack/nethack.cu'); t=N.read_text()
rep("""#define NH_MM_BR(A, W, O, BIAS) do { \\
    if (!nh_fused_br((A), (W), (O), (BIAS), stream)) { \\""",
"""#define NH_MM_BR(A, W, O, BIAS) do { \\
    if (!nh_small_mm((A), (W), (O), (BIAS).data, 1, stream) && !nh_fused_br((A), (W), (O), (BIAS), stream)) { \\""")
rep("""    int B = input.shape[0];
    if (nh_tables_external) nh_refresh_tables = false;""",
"""    int B = input.shape[0];
    if (nh_tables_external) nh_refresh_tables = false;
    g_small_gemm_infer = !a->training;""")
rep("""    int nopass, int passoff, const nh_obs_t* __restrict__ obs, int B) {
    int b = blockIdx.x;
    if (b >= B) return;
    const nh_obs_t* ob = obs + (int64_t)b * NH_OBS_SIZE;""",
"""    int nopass, int passoff, const nh_obs_t* __restrict__ obs, int B, const int* __restrict__ row_valid) {
    int b = blockIdx.x;
    if (b >= B) return;
    if (row_valid && row_valid[b] < 0) return;
    const nh_obs_t* ob = obs + (int64_t)b * NH_OBS_SIZE;""")
rep("""            NH_FRONT_NOPASS, NH_MINV_OFF + 2 * NH_MV, (const nh_obs_t*)input.data, B);""",
"""            NH_FRONT_NOPASS, NH_MINV_OFF + 2 * NH_MV, (const nh_obs_t*)input.data, B, (g_row_valid && B == g_row_valid_rows) ? g_row_valid : (const int*)NULL);""")
N.write_text(t)
P=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/pufferl.cu'); t=P.read_text()
rep("""        pufferl_forward_step(p, s, 0, stream);""",
"""        g_row_valid = vec->d_idx[s]; g_row_valid_rows = R; pufferl_forward_step(p, s, 0, stream); g_row_valid = NULL;""", count=0) if False else None
# two call sites in sched_forward_body (fold branch and original), 4-space and 8-space indents
n_before=t.count("pufferl_forward_step(p, s, 0, stream);"); assert n_before==2, n_before
t=t.replace("pufferl_forward_step(p, s, 0, stream);", "g_row_valid = vec->d_idx[s]; g_row_valid_rows = R; pufferl_forward_step(p, s, 0, stream); g_row_valid = NULL;")
rep("""            mask_b.data, mask_stride""", """            mask_b.data, mask_stride, (g_row_valid && n == g_row_valid_rows) ? g_row_valid : (const int*)NULL""")
P.write_text(t)
S=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/nethack_sampler.cuh'); t=S.read_text()
rep("""        precision_t* action_mask, int mask_stride""", """        precision_t* action_mask, int mask_stride, const int* row_valid""")
rep("""    static_assert(NUM_ATNS <= 32, "one lane per action head");""",
"""    static_assert(NUM_ATNS <= 32, "one lane per action head");
    if (row_valid && row_valid[blockIdx.x] < 0) return; /* padded scheduler row */""")
S.write_text(t); print('B2 applied')
