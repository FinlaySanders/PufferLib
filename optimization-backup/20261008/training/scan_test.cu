#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <cmath>
using precision_t=__nv_bfloat16;
struct Prec { precision_t* data; };
__host__ __device__ float to_float(precision_t v){return __bfloat162float(v);}
__host__ __device__ precision_t from_float(float v){return __float2bfloat16_rn(v);}
#define MINGRU_TILE 32
__device__ __forceinline__ float sigmoid(float x) {
    float z = expf(-fabsf(x));
    return x >= 0.0f ? 1.0f / (1.0f + z) : z / (1.0f + z);
}

__device__ __forceinline__ float lerp(float a, float b, float w) {
    float diff = b - a;
    return (fabsf(w) < 0.5f) ? a + w * diff : b - diff * (1.0f - w);
}

struct PrefixScan {
    precision_t* combined_ptr = NULL;
    precision_t* state_ptr = NULL;
    precision_t* input_ptr = NULL;  // (B, T, H) pre-projection input (highway)
    precision_t* terminals_ptr = NULL;  // (B, T), reset before step t if terminal[t]
    int B = 0, T = 0, H = 0;
    Prec scan_h;  // (B, T, H), recurrent input to each step
    Prec out, next_state;
    Prec grad_combined, grad_state;
    Prec grad_input;
};

__global__ void mingru_scan_forward_row_reference(PrefixScan scan) {
    int T_seq = scan.T, H = scan.H;
    int hx = threadIdx.x, t_local = threadIdx.y;
    int h = blockIdx.y * MINGRU_TILE + hx;
    int h_ok = h < H;
    int b = blockIdx.x, H3 = 3 * H, bHT = b * H * T_seq, cbase = 3 * bHT;
    float h_t = h_ok ? to_float(scan.state_ptr[b * H + h]) : 0.0f;
    __shared__ float sm_z[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_ht[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_s[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_x[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_term[MINGRU_TILE][MINGRU_TILE];
    for (int c = 0; c < (T_seq + MINGRU_TILE - 1) / MINGRU_TILE; c++) {
        int t = c * MINGRU_TILE + t_local;
        float z = 0.0f, h_tilde = 0.0f, s = 0.0f, x = 0.0f, term = 0.0f;
        if (t < T_seq && h_ok) {
            int off = t * H3 + h;
            float hidden = to_float(scan.combined_ptr[cbase + off]);
            float gate = to_float(scan.combined_ptr[cbase + H + off]);
            float proj = to_float(scan.combined_ptr[cbase + 2 * H + off]);
            x = to_float(scan.input_ptr[bHT + t * H + h]);
            z = sigmoid(gate);
            h_tilde = (hidden >= 0.0f) ? hidden + 0.5f : sigmoid(hidden);
            s = sigmoid(proj);
            term = scan.terminals_ptr != NULL &&
                to_float(scan.terminals_ptr[b * T_seq + t]) != 0.0f;
        }
        sm_z[t_local][hx] = z;
        sm_ht[t_local][hx] = h_tilde;
        sm_s[t_local][hx] = s;
        sm_x[t_local][hx] = x;
        sm_term[t_local][hx] = term;
        __syncthreads();
        if (t_local == 0 && h_ok) {
            int nloc = min(MINGRU_TILE, T_seq - c * MINGRU_TILE);
            for (int i = 0; i < nloc; i++) {
                if (sm_term[i][hx] != 0.0f) {
                    h_t = 0.0f;
                }
                int tt = c * MINGRU_TILE + i;
                scan.scan_h.data[bHT + tt * H + h] = from_float(h_t);
                h_t = lerp(h_t, sm_ht[i][hx], sm_z[i][hx]);
                float sv = sm_s[i][hx];
                scan.out.data[bHT + tt * H + h] =
                    from_float(sv * h_t + (1.0f - sv) * sm_x[i][hx]);
                h_t = to_float(from_float(h_t));
            }
        }
        __syncthreads();
    }
    if (t_local == 0 && h_ok) {
        scan.next_state.data[b * H + h] = from_float(h_t);
    }
}
__global__ void mingru_scan_backward_row_reference(PrefixScan scan,
        const precision_t* __restrict__ grad_out,
        const precision_t* __restrict__ grad_next_state) {
    int T_seq = scan.T, H = scan.H;
    int hx = threadIdx.x, t_local = threadIdx.y;
    int h = blockIdx.y * MINGRU_TILE + hx;
    int h_ok = h < H;
    int b = blockIdx.x, H3 = 3 * H, bHT = b * H * T_seq, cbase = 3 * bHT;
    float dh = h_ok ? to_float(grad_next_state[b * H + h]) : 0.0f;
    __shared__ float sm_z[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_ht[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_s[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_x[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_hp[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_go[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_hid[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_term[MINGRU_TILE][MINGRU_TILE];
    for (int c = (T_seq + MINGRU_TILE - 1) / MINGRU_TILE - 1; c >= 0; c--) {
        int t = c * MINGRU_TILE + t_local;
        float z = 0.0f, h_tilde = 0.0f, s = 0.0f, x = 0.0f;
        float h_prev = 0.0f, gout = 0.0f, hidden = 0.0f, term = 0.0f;
        if (t < T_seq && h_ok) {
            int off = t * H3 + h;
            hidden = to_float(scan.combined_ptr[cbase + off]);
            float gate = to_float(scan.combined_ptr[cbase + H + off]);
            float proj = to_float(scan.combined_ptr[cbase + 2 * H + off]);
            x = to_float(scan.input_ptr[bHT + t * H + h]);
            h_prev = to_float(scan.scan_h.data[bHT + t * H + h]);
            gout = to_float(grad_out[bHT + t * H + h]);
            z = sigmoid(gate);
            h_tilde = (hidden >= 0.0f) ? hidden + 0.5f : sigmoid(hidden);
            s = sigmoid(proj);
            term = scan.terminals_ptr != NULL &&
                to_float(scan.terminals_ptr[b * T_seq + t]) != 0.0f;
        }
        sm_z[t_local][hx] = z;
        sm_ht[t_local][hx] = h_tilde;
        sm_s[t_local][hx] = s;
        sm_x[t_local][hx] = x;
        sm_hp[t_local][hx] = h_prev;
        sm_go[t_local][hx] = gout;
        sm_hid[t_local][hx] = hidden;
        sm_term[t_local][hx] = term;
        __syncthreads();
        if (t_local == 0 && h_ok) {
            for (int i = min(MINGRU_TILE, T_seq - c * MINGRU_TILE) - 1; i >= 0; i--) {
                int tt = c * MINGRU_TILE + i;
                z = sm_z[i][hx];
                s = sm_s[i][hx];
                gout = sm_go[i][hx];
                h_tilde = sm_ht[i][hx];
                h_prev = sm_hp[i][hx];
                float h_t = lerp(h_prev, h_tilde, z);
                float dh_total = dh + gout * s;
                float d_h_tilde = dh_total * z;
                int off = tt * H3 + h;
                scan.grad_input.data[bHT + tt * H + h] =
                    from_float(gout * (1.0f - s));
                scan.grad_combined.data[cbase + off] = from_float(
                    sm_hid[i][hx] >= 0.0f ? d_h_tilde
                    : d_h_tilde * h_tilde * (1.0f - h_tilde));
                scan.grad_combined.data[cbase + H + off] =
                    from_float(dh_total * (h_tilde - h_prev) * z * (1.0f - z));
                scan.grad_combined.data[cbase + 2 * H + off] =
                    from_float(gout * (h_t - sm_x[i][hx]) * s * (1.0f - s));
                dh = sm_term[i][hx] != 0.0f ? 0.0f : dh_total * (1.0f - z);
            }
        }
        __syncthreads();
    }
    if (t_local == 0 && h_ok) {
        scan.grad_state.data[b * H + h] = from_float(dh);
    }
}

#define PUF_SCAN_PACK
#ifndef PUF_MINGRU_LOAD_ROWS
#define PUF_MINGRU_LOAD_ROWS 8
#endif
__global__ void mingru_scan_forward_row(PrefixScan scan) {
    int T_seq = scan.T, H = scan.H;
    int hx = threadIdx.x, t_local = threadIdx.y;
    int h = blockIdx.y * MINGRU_TILE + hx;
    int h_ok = h < H;
    int b = blockIdx.x, H3 = 3 * H, bHT = b * H * T_seq, cbase = 3 * bHT;
    float h_t = h_ok ? to_float(scan.state_ptr[b * H + h]) : 0.0f;
    __shared__ float sm_z[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_ht[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_s[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_x[MINGRU_TILE][MINGRU_TILE];
#ifdef PUF_SCAN_PACK
    __shared__ unsigned char sm_term[MINGRU_TILE];
#else
    __shared__ float sm_term[MINGRU_TILE][MINGRU_TILE];
#endif
    for (int c = 0; c < (T_seq + MINGRU_TILE - 1) / MINGRU_TILE; c++) {
        for(int load_t=t_local;load_t<MINGRU_TILE;load_t+=PUF_MINGRU_LOAD_ROWS) {
        int t = c * MINGRU_TILE + load_t;
        float z = 0.0f, h_tilde = 0.0f, s = 0.0f, x = 0.0f, term = 0.0f;
        if (t < T_seq && h_ok) {
            int off = t * H3 + h;
            float hidden = to_float(scan.combined_ptr[cbase + off]);
            float gate = to_float(scan.combined_ptr[cbase + H + off]);
            float proj = to_float(scan.combined_ptr[cbase + 2 * H + off]);
            x = to_float(scan.input_ptr[bHT + t * H + h]);
            z = sigmoid(gate);
            h_tilde = (hidden >= 0.0f) ? hidden + 0.5f : sigmoid(hidden);
            s = sigmoid(proj);
            term = scan.terminals_ptr != NULL &&
                to_float(scan.terminals_ptr[b * T_seq + t]) != 0.0f;
        }
        sm_z[load_t][hx] = z;
        sm_ht[load_t][hx] = h_tilde;
        sm_s[load_t][hx] = s;
        sm_x[load_t][hx] = x;
#ifdef PUF_SCAN_PACK
        if(hx==0)sm_term[load_t]=(unsigned char)term;
#else
        sm_term[load_t][hx] = term;
#endif
        }
        __syncthreads();
        if (t_local == 0 && h_ok) {
            int nloc = min(MINGRU_TILE, T_seq - c * MINGRU_TILE);
            for (int i = 0; i < nloc; i++) {
                if (
#ifdef PUF_SCAN_PACK
                    sm_term[i]
#else
                    sm_term[i][hx]
#endif
 != 0.0f) {
                    h_t = 0.0f;
                }
                int tt = c * MINGRU_TILE + i;
                scan.scan_h.data[bHT + tt * H + h] = from_float(h_t);
                h_t = lerp(h_t, sm_ht[i][hx], sm_z[i][hx]);
                float sv = sm_s[i][hx];
                scan.out.data[bHT + tt * H + h] =
                    from_float(sv * h_t + (1.0f - sv) * sm_x[i][hx]);
                h_t = to_float(from_float(h_t));
            }
        }
        __syncthreads();
    }
    if (t_local == 0 && h_ok) {
        scan.next_state.data[b * H + h] = from_float(h_t);
    }
}
__global__ void mingru_scan_backward_row(PrefixScan scan,
        const precision_t* __restrict__ grad_out,
        const precision_t* __restrict__ grad_next_state) {
    int T_seq = scan.T, H = scan.H;
    int hx = threadIdx.x, t_local = threadIdx.y;
    int h = blockIdx.y * MINGRU_TILE + hx;
    int h_ok = h < H;
    int b = blockIdx.x, H3 = 3 * H, bHT = b * H * T_seq, cbase = 3 * bHT;
    float dh = h_ok ? to_float(grad_next_state[b * H + h]) : 0.0f;
    __shared__ float sm_z[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_ht[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_s[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_x[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_hp[MINGRU_TILE][MINGRU_TILE];
    __shared__ float sm_go[MINGRU_TILE][MINGRU_TILE];
#ifdef PUF_SCAN_PACK
    __shared__ unsigned char sm_nonnegative[MINGRU_TILE][MINGRU_TILE];
#else
    __shared__ float sm_hid[MINGRU_TILE][MINGRU_TILE];
#endif
#ifdef PUF_SCAN_PACK
    __shared__ unsigned char sm_term[MINGRU_TILE];
#else
    __shared__ float sm_term[MINGRU_TILE][MINGRU_TILE];
#endif
    for (int c = (T_seq + MINGRU_TILE - 1) / MINGRU_TILE - 1; c >= 0; c--) {
        for(int load_t=t_local;load_t<MINGRU_TILE;load_t+=PUF_MINGRU_LOAD_ROWS) {
        int t = c * MINGRU_TILE + load_t;
        float z = 0.0f, h_tilde = 0.0f, s = 0.0f, x = 0.0f;
        float h_prev = 0.0f, gout = 0.0f, hidden = 0.0f, term = 0.0f;
        if (t < T_seq && h_ok) {
            int off = t * H3 + h;
            hidden = to_float(scan.combined_ptr[cbase + off]);
            float gate = to_float(scan.combined_ptr[cbase + H + off]);
            float proj = to_float(scan.combined_ptr[cbase + 2 * H + off]);
            x = to_float(scan.input_ptr[bHT + t * H + h]);
            h_prev = to_float(scan.scan_h.data[bHT + t * H + h]);
            gout = to_float(grad_out[bHT + t * H + h]);
            z = sigmoid(gate);
            h_tilde = (hidden >= 0.0f) ? hidden + 0.5f : sigmoid(hidden);
            s = sigmoid(proj);
            term = scan.terminals_ptr != NULL &&
                to_float(scan.terminals_ptr[b * T_seq + t]) != 0.0f;
        }
        sm_z[load_t][hx] = z;
        sm_ht[load_t][hx] = h_tilde;
        sm_s[load_t][hx] = s;
        sm_x[load_t][hx] = x;
        sm_hp[load_t][hx] = h_prev;
        sm_go[load_t][hx] = gout;
#ifdef PUF_SCAN_PACK
        sm_nonnegative[load_t][hx]=(hidden>=0.0f);
#else
        sm_hid[load_t][hx] = hidden;
#endif
#ifdef PUF_SCAN_PACK
        if(hx==0)sm_term[load_t]=(unsigned char)term;
#else
        sm_term[load_t][hx] = term;
#endif
        }
        __syncthreads();
        if (t_local == 0 && h_ok) {
            float z,s,gout,h_tilde,h_prev;
            for (int i = min(MINGRU_TILE, T_seq - c * MINGRU_TILE) - 1; i >= 0; i--) {
                int tt = c * MINGRU_TILE + i;
                z = sm_z[i][hx];
                s = sm_s[i][hx];
                gout = sm_go[i][hx];
                h_tilde = sm_ht[i][hx];
                h_prev = sm_hp[i][hx];
                float h_t = lerp(h_prev, h_tilde, z);
                float dh_total = dh + gout * s;
                float d_h_tilde = dh_total * z;
                int off = tt * H3 + h;
                scan.grad_input.data[bHT + tt * H + h] =
                    from_float(gout * (1.0f - s));
                scan.grad_combined.data[cbase + off] = from_float(
                    
#ifdef PUF_SCAN_PACK
                    sm_nonnegative[i][hx]
#else
                    sm_hid[i][hx] >= 0.0f
#endif
 ? d_h_tilde
                    : d_h_tilde * h_tilde * (1.0f - h_tilde));
                scan.grad_combined.data[cbase + H + off] =
                    from_float(dh_total * (h_tilde - h_prev) * z * (1.0f - z));
                scan.grad_combined.data[cbase + 2 * H + off] =
                    from_float(gout * (h_t - sm_x[i][hx]) * s * (1.0f - s));
                dh = 
#ifdef PUF_SCAN_PACK
                    sm_term[i]
#else
                    sm_term[i][hx]
#endif
 != 0.0f ? 0.0f : dh_total * (1.0f - z);
            }
        }
        __syncthreads();
    }
    if (t_local == 0 && h_ok) {
        scan.grad_state.data[b * H + h] = from_float(dh);
    }
}

std::vector<void*> allocated;
precision_t* buf(int n,bool randomize=false) {
 precision_t* p;assert(cudaMallocManaged(&p,n*sizeof(*p))==cudaSuccess);allocated.push_back(p);
 for(int i=0;i<n;i++)p[i]=from_float(randomize?(rand()%4001-2000)/100.f:0.f);return p;
}
void cmp(const char* name,precision_t* a,precision_t* b,int n) {
 for(int i=0;i<n;i++)if(memcmp(a+i,b+i,2)){printf("FAIL %s i=%d %.9g %.9g\n",name,i,to_float(a[i]),to_float(b[i]));exit(1);}
}
int main() {
 int cases[][3]={{1,1,1},{2,31,17},{3,33,65},{8,512,1024},{16,128,224},{5,257,31}};
 for(auto& c:cases)for(int resets=0;resets<2;resets++) {
  int B=c[0],T=c[1],H=c[2],n=B*T*H;PrefixScan a={},b={};a.B=b.B=B;a.T=b.T=T;a.H=b.H=H;
  a.combined_ptr=b.combined_ptr=buf(3*n,true);a.state_ptr=b.state_ptr=buf(B*H,true);a.input_ptr=b.input_ptr=buf(n,true);
  if(resets) {a.terminals_ptr=b.terminals_ptr=buf(B*T);for(int t=0;t<B*T;t++)a.terminals_ptr[t]=from_float(rand()%7==0?1.f:0.f);}
  for(auto* p:{&a,&b}) {p->scan_h={buf(n)};p->out={buf(n)};p->next_state={buf(B*H)};p->grad_combined={buf(3*n)};p->grad_input={buf(n)};p->grad_state={buf(B*H)};}
  auto* go=buf(n,true);auto* gs=buf(B*H,true);dim3 grid(B,(H+31)/32);
  mingru_scan_forward_row_reference<<<grid,dim3(32,32)>>>(a);
  mingru_scan_forward_row<<<grid,dim3(32,PUF_MINGRU_LOAD_ROWS)>>>(b);
  mingru_scan_backward_row_reference<<<grid,dim3(32,32)>>>(a,go,gs);
  mingru_scan_backward_row<<<grid,dim3(32,PUF_MINGRU_LOAD_ROWS)>>>(b,go,gs);
  assert(cudaDeviceSynchronize()==cudaSuccess);
  cmp("h",a.scan_h.data,b.scan_h.data,n);cmp("out",a.out.data,b.out.data,n);cmp("state",a.next_state.data,b.next_state.data,B*H);
  cmp("dc",a.grad_combined.data,b.grad_combined.data,3*n);cmp("dx",a.grad_input.data,b.grad_input.data,n);cmp("ds",a.grad_state.data,b.grad_state.data,B*H);
  printf("PASS B=%d T=%d H=%d resets=%d\n",B,T,H,resets);
  for(void* p:allocated)cudaFree(p);allocated.clear();
 }
}
