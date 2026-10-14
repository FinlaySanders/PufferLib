"""Stage B3: (1) tables refresh keyed on the actor-parameter copy at rollout start (exact); (2) tensor-core (wmma bf16, fp32 accumulate)
GEMM for all inference matmuls incl. the minGRU input projection (gate kernel unchanged) and the decoder; (3) dump keyed by agent step."""
from pathlib import Path
def rep(t,old,new,count=1):
    assert t.count(old)==count, (t.count(old), old[:90]); return t.replace(old,new)
A=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/algo.cu'); t=A.read_text()
s=t.index("// ===== Stage B2 (14 Oct 2026)"); e=t.index("Prec decoder_forward(void* w, void* activations, Prec input, cudaStream_t stream) {")
gemm='''// ===== Stage B2/B3 (14 Oct 2026): tensor-core GEMM for inference rows (NH_GEMM_FUSED=1) =====
// out[m,n] = relu?(sum_k A[m,k] W[n,k] + bias[n]); bf16 operands, fp32 accumulate on tensor cores (wmma 16x16x16), 64x64 block tiles,
// one launch per matmul; blocks whose first row is a padded scheduler row exit at once. Same operand convention as puf_mm.
#include <mma.h>
thread_local const int* g_row_valid = NULL; thread_local int g_row_valid_rows = 0; thread_local bool g_small_gemm_infer = false;
static int nh_gemm_fused_env() { static int v = -1; if (v < 0) v = getenv("NH_GEMM_FUSED") ? atoi(getenv("NH_GEMM_FUSED")) : 0; return v; }
#define WG_BM 64
#define WG_BN 64
#define WG_BK 32
__global__ void __launch_bounds__(256) wmma_gemm_kernel(const __nv_bfloat16* __restrict__ A, const __nv_bfloat16* __restrict__ W,
        __nv_bfloat16* __restrict__ O, const __nv_bfloat16* __restrict__ bias, int relu, int M, int N, int K, const int* __restrict__ row_valid) {
    using namespace nvcuda;
    int m0 = blockIdx.x * WG_BM, n0 = blockIdx.y * WG_BN;
    if (row_valid && row_valid[m0] < 0) return;
    __shared__ __align__(32) __nv_bfloat16 As[WG_BM][WG_BK];
    __shared__ __align__(32) __nv_bfloat16 Ws[WG_BN][WG_BK];
    __shared__ __align__(32) float Cs[WG_BM][WG_BN];
    int t = threadIdx.x, warp = t >> 5, wm = warp >> 1, wn = warp & 1;
    wmma::fragment<wmma::accumulator, 16, 16, 16, float> acc[2];
    wmma::fill_fragment(acc[0], 0.f); wmma::fill_fragment(acc[1], 0.f);
    const bool vec8 = (K % 8) == 0;
    for (int k0 = 0; k0 < K; k0 += WG_BK) {
        if (vec8) { /* 8 bf16 per thread per tile */
            { int r = t >> 2, k = (t & 3) * 8; int gm = m0 + r, gk = k0 + k;
              uint4 v = (gm < M && gk < K) ? *(const uint4*)(A + (long)gm * K + gk) : make_uint4(0, 0, 0, 0); *(uint4*)&As[r][k] = v; }
            { int c = t >> 2, k = (t & 3) * 8; int gn = n0 + c, gk = k0 + k;
              uint4 v = (gn < N && gk < K) ? *(const uint4*)(W + (long)gn * K + gk) : make_uint4(0, 0, 0, 0); *(uint4*)&Ws[c][k] = v; }
        } else {
            for (int i = t; i < WG_BM * WG_BK; i += 256) { int r = i / WG_BK, k = i % WG_BK; int gm = m0 + r, gk = k0 + k;
                As[r][k] = (gm < M && gk < K) ? A[(long)gm * K + gk] : __float2bfloat16(0.f); }
            for (int i = t; i < WG_BN * WG_BK; i += 256) { int c = i / WG_BK, k = i % WG_BK; int gn = n0 + c, gk = k0 + k;
                Ws[c][k] = (gn < N && gk < K) ? W[(long)gn * K + gk] : __float2bfloat16(0.f); }
        }
        __syncthreads();
        #pragma unroll
        for (int kk = 0; kk < WG_BK; kk += 16) {
            wmma::fragment<wmma::matrix_a, 16, 16, 16, __nv_bfloat16, wmma::row_major> fa;
            wmma::load_matrix_sync(fa, &As[wm * 16][kk], WG_BK);
            #pragma unroll
            for (int j = 0; j < 2; j++) {
                wmma::fragment<wmma::matrix_b, 16, 16, 16, __nv_bfloat16, wmma::col_major> fb;
                wmma::load_matrix_sync(fb, &Ws[wn * 32 + j * 16][kk], WG_BK);
                wmma::mma_sync(acc[j], fa, fb, acc[j]);
            }
        }
        __syncthreads();
    }
    wmma::store_matrix_sync(&Cs[wm * 16][wn * 32], acc[0], WG_BN, wmma::mem_row_major);
    wmma::store_matrix_sync(&Cs[wm * 16][wn * 32 + 16], acc[1], WG_BN, wmma::mem_row_major);
    __syncthreads();
    for (int i = t; i < WG_BM * WG_BN; i += 256) {
        int r = i / WG_BN, c = i % WG_BN; int gm = m0 + r, gn = n0 + c;
        if (gm >= M || gn >= N) continue;
        float v = Cs[r][c] + (bias ? __bfloat162float(bias[gn]) : 0.f);
        if (relu) v = fmaxf(v, 0.f);
        O[(long)gm * N + gn] = __float2bfloat16(v);
    }
}
static bool nh_small_mm_raw(const precision_t* A, const precision_t* W, precision_t* O, const precision_t* bias, int relu, int M, int N, int K, cudaStream_t stream) {
    if (!nh_gemm_fused_env() || !g_small_gemm_infer || M <= 0 || N <= 0 || K <= 0) return false;
    const int* rv = (g_row_valid && M == g_row_valid_rows) ? g_row_valid : NULL;
    dim3 grid((M + WG_BM - 1) / WG_BM, (N + WG_BN - 1) / WG_BN);
    wmma_gemm_kernel<<<grid, 256, 0, stream>>>((const __nv_bfloat16*)A, (const __nv_bfloat16*)W, (__nv_bfloat16*)O, (const __nv_bfloat16*)bias, relu, M, N, K, rv);
    return true;
}
// Same operand convention as puf_mm: out(M,N) = a(M,K) @ b(N,K)^T (+ bias[N]) (relu)
static bool nh_small_mm(Prec* a, Prec* b, Prec* out, const precision_t* bias, int relu, cudaStream_t stream) {
    int M = batch_size(a->shape) * a->shape[ndim(a->shape)-2];
    int K = a->shape[ndim(a->shape)-1];
    int N = b->shape[ndim(b->shape)-2];
    return nh_small_mm_raw(a->data, b->data, out->data, bias, relu, M, N, K, stream);
}
'''
t=t[:s]+gemm+t[e:]
# minGRU: replace the B1 fused layer with GEMM(tensor core) + the original gate kernel
s=t.index("// ===== Stage B1 (14 Oct 2026)"); e=t.index("Prec mingru_forward(void* w, Prec x, Prec state,")
t=t[:s]+'''// Stage B3: the minGRU input projection runs on the tensor-core GEMM when NH_GEMM_FUSED=1 (gate kernel unchanged, same aliasing as NOCOPY)
'''+t[e:]
t=rep(t,"""        if (mingru_fused_try(x.data, m->weights[i].data, state_i.data, fused_out.data, B, H, stream)) { x = fused_out; continue; }
""","""        if (nh_small_mm(&x, &m->weights[i], &a->combined[i], NULL, 0, stream)) {
            mingru_gate<<<grid_size(B*H), BLOCK_SIZE, 0, stream>>>(a->out.data, state_i.data, a->combined[i].data, state_i.data, x.data, H, B);
            x = a->out; continue;
        }
""")
A.write_text(t)
P=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/pufferl.cu'); t=P.read_text()
t=rep(t,"""    Prec actor_param;      // async flat actor params""","""    Prec actor_param;      // async flat actor params
    long actor_param_version; // bumped at every rollout start (weights the rollout will use are fixed from here)""")
t=rep(t,"""    p->write_slot = slot;
    if (p->hypers.async) {
        Prec* param = &p->policies[0].param;""","""    p->write_slot = slot;
    p->actor_param_version++;
    if (p->hypers.async) {
        Prec* param = &p->policies[0].param;""")
t=rep(t,"""        if (tables_ext && table_epoch != (long)p->epoch) { /* vocabulary tables depend only on the weights: once per epoch, outside the graph */
            Policy* pol = &p->policies[0]; Weights* w = (!pol->frozen && p->hypers.async) ? &p->actor_weights : &pol->weights;
            nethack_encoder_refresh_tables(w->encoder, pol->buf_acts[s].encoder, stream); table_epoch = (long)p->epoch;
        }""","""        if (tables_ext && table_epoch != p->actor_param_version) { /* vocabulary tables depend only on the rollout's weights: once per rollout start, outside the graph */
            Policy* pol = &p->policies[0]; Weights* w = (!pol->frozen && p->hypers.async) ? &p->actor_weights : &pol->weights;
            nethack_encoder_refresh_tables(w->encoder, pol->buf_acts[s].encoder, stream); table_epoch = p->actor_param_version;
        }""")
t=rep(t,"""            for (int r = 0; r < n; r++) fprintf(df, "%ld %d %d %.6g %.6g\\n", vec->sched_forwards[s], r, idx[r], (double)to_float(hl[r]), (double)to_float(hl[R + r]));""",
"""            for (int r = 0; r < n; r++) fprintf(df, "%ld %d %d %d %.6g %.6g\\n", vec->sched_forwards[s], r, idx[r], tt[r], (double)to_float(hl[r]), (double)to_float(hl[R + r]));""")
P.write_text(t); print('B3 applied')
