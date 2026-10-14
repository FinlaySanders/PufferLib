
#include <cuda_bf16.h>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <mma.h>
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

static float bf(float x) { return __bfloat162float(__float2bfloat16(x)); }
int run(int M, int N, int K, int relu, int use_bias, int cutoff) {
    std::vector<float> A(M*(size_t)K), W(N*(size_t)K), bias(N);
    srand(1234);
    for (auto& v : A) v = bf((rand() / (float)RAND_MAX - 0.5f) * 2.f);
    for (auto& v : W) v = bf((rand() / (float)RAND_MAX - 0.5f) * 0.1f);
    for (auto& v : bias) v = bf((rand() / (float)RAND_MAX - 0.5f));
    std::vector<__nv_bfloat16> hA(M*(size_t)K), hW(N*(size_t)K), hb(N);
    for (size_t i = 0; i < hA.size(); i++) hA[i] = __float2bfloat16(A[i]);
    for (size_t i = 0; i < hW.size(); i++) hW[i] = __float2bfloat16(W[i]);
    for (int i = 0; i < N; i++) hb[i] = __float2bfloat16(bias[i]);
    std::vector<int> rv(M, 0); if (cutoff > 0) for (int i = cutoff; i < M; i++) rv[i] = -1;
    __nv_bfloat16 *dA, *dW, *dO, *db; int* drv;
    cudaMalloc(&dA, hA.size()*2); cudaMalloc(&dW, hW.size()*2); cudaMalloc(&dO, (size_t)M*N*2); cudaMalloc(&db, N*2); cudaMalloc(&drv, M*4);
    cudaMemcpy(dA, hA.data(), hA.size()*2, cudaMemcpyHostToDevice); cudaMemcpy(dW, hW.data(), hW.size()*2, cudaMemcpyHostToDevice);
    cudaMemcpy(db, hb.data(), N*2, cudaMemcpyHostToDevice); cudaMemcpy(drv, rv.data(), M*4, cudaMemcpyHostToDevice);
    cudaMemset(dO, 0, (size_t)M*N*2);
    dim3 grid((M + WG_BM - 1) / WG_BM, (N + WG_BN - 1) / WG_BN);
    cudaEvent_t e0, e1; cudaEventCreate(&e0); cudaEventCreate(&e1);
    wmma_gemm_kernel<<<grid, 256>>>(dA, dW, dO, use_bias ? db : NULL, relu, M, N, K, cutoff > 0 ? drv : NULL);
    cudaEventRecord(e0); for (int i = 0; i < 20; i++) wmma_gemm_kernel<<<grid, 256>>>(dA, dW, dO, use_bias ? db : NULL, relu, M, N, K, cutoff > 0 ? drv : NULL); cudaEventRecord(e1);
    cudaError_t err = cudaDeviceSynchronize(); if (err != cudaSuccess) { printf("CUDA error %s\n", cudaGetErrorString(err)); return 1; }
    float ms; cudaEventElapsedTime(&ms, e0, e1);
    std::vector<__nv_bfloat16> hO((size_t)M*N); cudaMemcpy(hO.data(), dO, hO.size()*2, cudaMemcpyDeviceToHost);
    double maxd = 0, sumd = 0; long n = 0; int bad = 0;
    int Mchk = cutoff > 0 ? ((cutoff + WG_BM - 1) / WG_BM) * WG_BM : M; if (Mchk > M) Mchk = M;
    for (int m = 0; m < Mchk; m++) for (int nn = 0; nn < N; nn++) {
        double acc = 0; for (int k = 0; k < K; k++) acc += (double)A[(size_t)m*K+k] * W[(size_t)nn*K+k];
        float ref = (float)acc + (use_bias ? bias[nn] : 0.f); if (relu) ref = ref > 0 ? ref : 0; float refb = bf(ref);
        float got = __bfloat162float(hO[(size_t)m*N+nn]); double d = fabs(got - refb); double tol = fabs(refb) * 0.01 + 1e-2;
        if (d > tol) bad++; if (d > maxd) maxd = d; sumd += d; n++;
    }
    printf("M=%d N=%d K=%d relu=%d bias=%d cutoff=%d : max|diff| %.4g mean %.4g bad %d/%ld  (%.1f us/launch)\n", M, N, K, relu, use_bias, cutoff, maxd, sumd/n, bad, n, ms*1000/20);
    cudaFree(dA); cudaFree(dW); cudaFree(dO); cudaFree(db); cudaFree(drv); return bad ? 1 : 0;
}
int main() { int r = 0;
    r |= run(130, 64, 48, 1, 1, 0); r |= run(130, 512, 1698, 1, 1, 0); r |= run(512, 1536, 512, 0, 0, 0); r |= run(512, 731, 512, 0, 0, 0);
    r |= run(512, 512, 1698, 1, 1, 110); r |= run(512, 1536, 512, 0, 0, 110); r |= run(200, 100, 24, 1, 1, 0);
    printf(r ? "FAIL\n" : "ALL OK\n"); return r; }
