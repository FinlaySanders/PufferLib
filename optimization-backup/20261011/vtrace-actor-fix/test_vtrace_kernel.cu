// puff_advantage: shipped kernel vs actor-fix kernel vs double reference.
// nvcc -O2 -std=c++17 -arch=native [-DPRECISION_FLOAT] test_vtrace_kernel.cu -o t && ./t
#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <vector>
#include <random>

#ifdef PRECISION_FLOAT
typedef float precision_t;
#define to_float(x) (x)
#define from_float(x) (x)
static const char* PREC = "float";
#else
typedef __nv_bfloat16 precision_t;
#define to_float(x) __bfloat162float(x)
#define from_float(x) __float2bfloat16(x)
static const char* PREC = "bf16";
#endif
constexpr int ADV_VEC_WIDTH = 16 / (int)sizeof(precision_t);

#define CK(x) do { cudaError_t e = (x); if (e != cudaSuccess) { \
    fprintf(stderr, "CUDA %d %s\n", __LINE__, cudaGetErrorString(e)); exit(1); } } while (0)

__device__ __forceinline__ void adv_ld(const precision_t* p, float* o) {
    if constexpr (sizeof(precision_t) == sizeof(float)) {
        float4 v = *(const float4*)p;
        o[0] = v.x; o[1] = v.y; o[2] = v.z; o[3] = v.w;
    } else {
        uint4 u = *(const uint4*)p;
        auto* b = (const __nv_bfloat16*)&u;
        #pragma unroll
        for (int i = 0; i < 8; i++) o[i] = __bfloat162float(b[i]);
    }
}
__device__ __forceinline__ void adv_st(precision_t* p, const float* o) {
    if constexpr (sizeof(precision_t) == sizeof(float)) {
        *(float4*)p = make_float4(o[0], o[1], o[2], o[3]);
    } else {
        __nv_bfloat16 b[8];
        #pragma unroll
        for (int i = 0; i < 8; i++) b[i] = __float2bfloat16(o[i]);
        *(uint4*)p = *(const uint4*)b;
    }
}

// ---- shipped kernel (src/algo.cu @3719caaa) ----
__global__ void puff_advantage_old(const precision_t* values,
        const precision_t* rewards, const precision_t* dones,
        const precision_t* importance, precision_t* advantages,
        precision_t* returns,
        float gamma, float lambda, float rho_clip, float c_clip,
        int num_steps, int horizon) {
    int row = blockIdx.x * blockDim.x + threadIdx.x;
    if (row >= num_steps) return;
    int off = row * horizon;
    float lastlam = 0.f;
    float next_v = to_float(values[off + horizon - 1]);
    float next_d = to_float(dones[off + horizon - 1]);
    float next_r = to_float(rewards[off + horizon - 1]);
    for (int seg = horizon / ADV_VEC_WIDTH - 1; seg >= 0; seg--) {
        int base = off + seg * ADV_VEC_WIDTH;
        float v[ADV_VEC_WIDTH], r[ADV_VEC_WIDTH], d[ADV_VEC_WIDTH], imp[ADV_VEC_WIDTH];
        float adv[ADV_VEC_WIDTH] = {};
        float ret[ADV_VEC_WIDTH];
        adv_ld(values + base, v);
        adv_ld(rewards + base, r);
        adv_ld(dones + base, d);
        if (importance) {
            adv_ld(importance + base, imp);
        } else {
            #pragma unroll
            for (int i = 0; i < ADV_VEC_WIDTH; i++) imp[i] = 1.f;
        }
        int i0 = (seg + 1 == horizon / ADV_VEC_WIDTH) ? ADV_VEC_WIDTH - 2 : ADV_VEC_WIDTH - 1;
        #pragma unroll
        for (int i = i0; i >= 0; i--) {
            float nnt = 1.f - next_d;
            float rho_t = fminf(imp[i], rho_clip);
            float c_t = fminf(imp[i], c_clip);
            float delta = rho_t * (next_r + gamma * next_v * nnt - v[i]);
            lastlam = delta + gamma * lambda * c_t * lastlam * nnt;
            adv[i] = lastlam;
            next_v = v[i]; next_d = d[i]; next_r = r[i];
        }
        #pragma unroll
        for (int i = 0; i < ADV_VEC_WIDTH; i++) ret[i] = v[i] + adv[i];
        adv_st(advantages + base, adv);
        adv_st(returns + base, ret);
    }
}

// ---- actor-fix kernel (vtrace_actor_fix.patch) ----
__global__ void puff_advantage_new(const precision_t* values,
        const precision_t* rewards, const precision_t* dones,
        const precision_t* importance, precision_t* advantages,
        precision_t* returns,
        float gamma, float lambda, float rho_clip, float c_clip,
        int num_steps, int horizon) {
    int row = blockIdx.x * blockDim.x + threadIdx.x;
    if (row >= num_steps) return;
    int off = row * horizon;
    const bool is = importance != NULL;
    float lastlam = 0.f;
    float next_v = to_float(values[off + horizon - 1]);
    float next_d = to_float(dones[off + horizon - 1]);
    float next_r = to_float(rewards[off + horizon - 1]);
    for (int seg = horizon / ADV_VEC_WIDTH - 1; seg >= 0; seg--) {
        int base = off + seg * ADV_VEC_WIDTH;
        float v[ADV_VEC_WIDTH], r[ADV_VEC_WIDTH], d[ADV_VEC_WIDTH];
        float imp[ADV_VEC_WIDTH] = {};
        float adv[ADV_VEC_WIDTH] = {};
        float res[ADV_VEC_WIDTH] = {};
        float ret[ADV_VEC_WIDTH];
        adv_ld(values + base, v);
        adv_ld(rewards + base, r);
        adv_ld(dones + base, d);
        if (is) {
            adv_ld(importance + base, imp);
        }
        int i0 = (seg + 1 == horizon / ADV_VEC_WIDTH) ? ADV_VEC_WIDTH - 2 : ADV_VEC_WIDTH - 1;
        #pragma unroll
        for (int i = i0; i >= 0; i--) {
            float nnt = 1.f - next_d;
            float delta = next_r + gamma * next_v * nnt - v[i];
            if (is) {
                float rho_t = fminf(imp[i], rho_clip);
                float c_t = fminf(imp[i], c_clip);
                float tail = gamma * lambda * lastlam * nnt;
                adv[i] = delta + tail;
                lastlam = rho_t * delta + c_t * tail;
            } else {
                lastlam = delta + gamma * lambda * lastlam * nnt;
                adv[i] = lastlam;
            }
            res[i] = lastlam;
            next_v = v[i]; next_d = d[i]; next_r = r[i];
        }
        #pragma unroll
        for (int i = 0; i < ADV_VEC_WIDTH; i++) ret[i] = v[i] + res[i];
        adv_st(advantages + base, adv);
        adv_st(returns + base, ret);
    }
}

struct Out { std::vector<float> adv, ret; std::vector<unsigned char> adv_bits, ret_bits; };
typedef void (*Kern)(const precision_t*, const precision_t*, const precision_t*,
    const precision_t*, precision_t*, precision_t*, float, float, float, float, int, int);

static Out run(Kern k, precision_t* dv, precision_t* dr, precision_t* dd, precision_t* di,
        precision_t* da, precision_t* dret, float g, float l, float rho, float c, int B, int T) {
    size_t n = (size_t)B * T, bytes = n * sizeof(precision_t);
    CK(cudaMemset(da, 0, bytes)); CK(cudaMemset(dret, 0, bytes));
    k<<<(B + 63) / 64, 64>>>(dv, dr, dd, di, da, dret, g, l, rho, c, B, T);
    CK(cudaDeviceSynchronize());
    Out o; o.adv_bits.resize(bytes); o.ret_bits.resize(bytes);
    CK(cudaMemcpy(o.adv_bits.data(), da, bytes, cudaMemcpyDeviceToHost));
    CK(cudaMemcpy(o.ret_bits.data(), dret, bytes, cudaMemcpyDeviceToHost));
    o.adv.resize(n); o.ret.resize(n);
    for (size_t i = 0; i < n; i++) {
        o.adv[i] = to_float(((precision_t*)o.adv_bits.data())[i]);
        o.ret[i] = to_float(((precision_t*)o.ret_bits.data())[i]);
    }
    return o;
}

struct Ref { std::vector<double> Av, Apg, ret, rho_w; };
static Ref reference(const std::vector<float>& v, const std::vector<float>& r,
        const std::vector<float>& d, const std::vector<float>* w,
        double g, double l, double rho_clip, double c_clip, int B, int T) {
    size_t n = (size_t)B * T;
    Ref R; R.Av.assign(n, 0); R.Apg.assign(n, 0); R.ret.assign(n, 0); R.rho_w.assign(n, 1);
    for (int b = 0; b < B; b++) {
        size_t off = (size_t)b * T;
        R.ret[off + T - 1] = v[off + T - 1];
        for (int t = T - 2; t >= 0; t--) {
            double nnt = 1.0 - d[off + t + 1];
            double delta = r[off + t + 1] + g * v[off + t + 1] * nnt - v[off + t];
            double wt = w ? (*w)[off + t] : 1.0;
            double rho = w ? std::min(wt, rho_clip) : 1.0;
            double c = w ? std::min(wt, c_clip) : 1.0;
            double tail = g * l * nnt * R.Av[off + t + 1];
            R.Apg[off + t] = delta + tail;
            R.Av[off + t] = rho * delta + c * tail;
            R.ret[off + t] = v[off + t] + R.Av[off + t];
            R.rho_w[off + t] = rho;
        }
    }
    return R;
}

static double tol_rel, tol_abs;
static int fails = 0;
static void check(const char* name, const std::vector<float>& got, const std::vector<double>& want,
        const std::vector<double>* scale = NULL) {
    double maxerr = 0, maxrel = 0; size_t bad = 0, worst = 0;
    for (size_t i = 0; i < got.size(); i++) {
        double w = scale ? want[i] * (*scale)[i] : want[i];
        double e = fabs(got[i] - w), tol = tol_abs + tol_rel * fabs(w);
        if (e > tol) bad++;
        if (e > maxerr) { maxerr = e; worst = i; }
        if (fabs(w) > 1e-2) maxrel = std::max(maxrel, e / fabs(w));
    }
    bool ok = bad == 0; if (!ok) fails++;
    printf("  %-44s %s  max_abs %.3g max_rel %.3g  bad %zu/%zu%s\n", name, ok ? "PASS" : "FAIL",
        maxerr, maxrel, bad, got.size(), bad ? "" : "");
    if (!ok) printf("    worst idx %zu got %.6f want %.6f\n", worst, got[worst],
        scale ? want[worst] * (*scale)[worst] : want[worst]);
}
static void check_bits(const char* name, const std::vector<unsigned char>& a,
        const std::vector<unsigned char>& b) {
    bool ok = a == b; if (!ok) fails++;
    size_t diff = 0; for (size_t i = 0; i < a.size(); i++) diff += a[i] != b[i];
    printf("  %-44s %s  differing bytes %zu/%zu\n", name, ok ? "PASS" : "FAIL", diff, a.size());
}

int main() {
    const int B = 512, T = 64;
    const float g = 0.995f, l = 0.90f;
    size_t n = (size_t)B * T, bytes = n * sizeof(precision_t);
#ifdef PRECISION_FLOAT
    tol_rel = 2e-5; tol_abs = 2e-5;
#else
    tol_rel = 4.5e-3; tol_abs = 1e-4;  // bf16 output rounding (2^-8 relative)
#endif
    printf("puff_advantage check  precision=%s  B=%d T=%d gamma=%g lambda=%g\n", PREC, B, T, g, l);

    std::mt19937 rng(1234);
    std::normal_distribution<float> N01(0.f, 1.f);
    std::uniform_real_distribution<float> U(-1.f, 1.f), U01(0.f, 1.f);
    std::vector<precision_t> hv(n), hr(n), hd(n), hw(n);
    std::vector<float> fv(n), fr(n), fd(n), fw(n);
    for (size_t i = 0; i < n; i++) {
        hv[i] = from_float(2.f * N01(rng)); hr[i] = from_float(U(rng));
        hd[i] = from_float(U01(rng) < 0.05f ? 1.f : 0.f);
        hw[i] = from_float(expf(0.3f * N01(rng)));
        fv[i] = to_float(hv[i]); fr[i] = to_float(hr[i]); fd[i] = to_float(hd[i]); fw[i] = to_float(hw[i]);
    }
    precision_t *dv, *dr, *dd, *dw, *da, *dret;
    CK(cudaMalloc(&dv, bytes)); CK(cudaMalloc(&dr, bytes)); CK(cudaMalloc(&dd, bytes));
    CK(cudaMalloc(&dw, bytes)); CK(cudaMalloc(&da, bytes)); CK(cudaMalloc(&dret, bytes));
    CK(cudaMemcpy(dv, hv.data(), bytes, cudaMemcpyHostToDevice));
    CK(cudaMemcpy(dr, hr.data(), bytes, cudaMemcpyHostToDevice));
    CK(cudaMemcpy(dd, hd.data(), bytes, cudaMemcpyHostToDevice));
    CK(cudaMemcpy(dw, hw.data(), bytes, cudaMemcpyHostToDevice));

    printf("[1] vtrace=0 (importance NULL): default path must be bit-identical\n");
    Out o0 = run(puff_advantage_old, dv, dr, dd, NULL, da, dret, g, l, 1.f, 1.f, B, T);
    Out n0 = run(puff_advantage_new, dv, dr, dd, NULL, da, dret, g, l, 1.f, 1.f, B, T);
    check_bits("old vs new advantages (bits)", o0.adv_bits, n0.adv_bits);
    check_bits("old vs new returns (bits)", o0.ret_bits, n0.ret_bits);
    Ref g0 = reference(fv, fr, fd, NULL, g, l, 1, 1, B, T);
    check("new advantages vs GAE reference", n0.adv, g0.Apg);
    check("new returns vs GAE reference", n0.ret, g0.ret);

    struct Case { const char* name; float rho, c; } cases[] = {
        {"rho_clip=1 c_clip=1 (defaults)", 1.f, 1.f},
        {"rho_clip=1 c_clip=0.5", 1.f, 0.5f},
        {"rho_clip=2 c_clip=1", 2.f, 1.f},
        {"rho_clip=inf c_clip=inf (full IS)", 1e30f, 1e30f},
    };
    int ci = 2;
    for (auto& cs : cases) {
        printf("[%d] vtrace=1 %s\n", ci++, cs.name);
        Out o = run(puff_advantage_old, dv, dr, dd, dw, da, dret, g, l, cs.rho, cs.c, B, T);
        Out nw = run(puff_advantage_new, dv, dr, dd, dw, da, dret, g, l, cs.rho, cs.c, B, T);
        Ref R = reference(fv, fr, fd, &fw, g, l, cs.rho, cs.c, B, T);
        check("old returns vs V-trace target", o.ret, R.ret);
        check("new returns vs V-trace target", nw.ret, R.ret);
        check("old advantages vs critic residual A_v", o.adv, R.Av);
        check("new advantages vs actor A_pg", nw.adv, R.Apg);
        if (cs.rho == cs.c) check("old advantages vs rho_t * A_pg (factorisation)", o.adv, R.Apg, &R.rho_w);
        // Size of the extra actor factor in the shipped kernel.
        double sum = 0, cnt = 0, mn = 1e9, shrunk = 0;
        for (size_t i = 0; i < n; i++) {
            if ((i % T) == (size_t)T - 1 || fabs(R.Apg[i]) < 1e-3) continue;
            double f = o.adv[i] / nw.adv[i];
            sum += f; cnt++; mn = std::min(mn, f); if (f < 0.99) shrunk++;
        }
        printf("    shipped/actor advantage ratio: mean %.4f min %.4f  steps scaled <0.99: %.1f%%\n",
            sum / cnt, mn, 100.0 * shrunk / cnt);
    }
    printf("%s  precision=%s  failures=%d\n", fails ? "RESULT FAIL" : "RESULT PASS", PREC, fails);
    return fails ? 1 : 0;
}
