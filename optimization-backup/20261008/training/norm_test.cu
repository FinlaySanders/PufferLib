#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <vector>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cmath>
typedef __nv_bfloat16 precision_t;
__device__ float to_float(precision_t x){return __bfloat162float(x);}
__device__ precision_t from_float(float x){return __float2bfloat16(x);}
__device__ __forceinline__ void block_reduce_sum(
        float* smem, float* out, int tid, int nthreads, int nchan) {
    __syncthreads();
    for (int s = nthreads / 2; s > 0; s >>= 1) {
        if (tid < s) {
            for (int c = 0; c < nchan; c++) {
                smem[c * nthreads + tid] += smem[c * nthreads + tid + s];
            }
        }
        __syncthreads();
    }
    if (tid == 0) {
        for (int c = 0; c < nchan; c++) {
            out[c] = smem[c * nthreads];
        }
    }
}__global__ void muon_sum_sq_partials(float* __restrict__ partials,
        const precision_t* __restrict__ src, int n) {
    __shared__ float sdata[256];
    int tid = threadIdx.x;
    float sum = 0.0f;
    for (int i = blockIdx.x * blockDim.x + tid; i < n; i += blockDim.x * gridDim.x) {
        float v = to_float(src[i]);
        sum += v * v;
    }
    sdata[tid] = sum;
    block_reduce_sum(sdata, &partials[blockIdx.x], tid, blockDim.x, 1);
}

__global__ void muon_sum_sq_reduce(float* __restrict__ out,
        const float* __restrict__ partials, int num_blocks) {
    __shared__ float sdata[256];
    int tid = threadIdx.x;
    sdata[tid] = (tid < num_blocks) ? partials[tid] : 0.0f;
    block_reduce_sum(sdata, out, tid, blockDim.x, 1);
}

__global__ void muon_l2_normalize(precision_t* __restrict__ dst,
        const float* __restrict__ sum_sq_ptr, float eps, int n) {
    float inv_norm = 1.0f / fmaxf(sqrtf(*sum_sq_ptr), eps);
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        dst[idx] = from_float(to_float(dst[idx]) * inv_norm);
    }
}

struct MuonNormDesc { long offset; int n, blocks; };
__global__ void muon_norm_batch_partials(float* partials, const precision_t* src, const MuonNormDesc* desc) {
    MuonNormDesc d=desc[blockIdx.y];
    if (blockIdx.x >= d.blocks) return;
    __shared__ float sdata[256];
    int tid=threadIdx.x;float sum=0.0f;
    for(int i=blockIdx.x*256+tid;i<d.n;i+=256*d.blocks) { float v=to_float(src[d.offset+i]);sum+=v*v; }
    sdata[tid]=sum;
    block_reduce_sum(sdata,&partials[blockIdx.y*256+blockIdx.x],tid,256,1);
}
__global__ void muon_norm_batch_reduce(float* out,const float* partials,const MuonNormDesc* desc) {
    __shared__ float sdata[256];int tid=threadIdx.x;
    sdata[tid]=tid<desc[blockIdx.x].blocks?partials[blockIdx.x*256+tid]:0.0f;
    block_reduce_sum(sdata,&out[blockIdx.x],tid,256,1);
}
__global__ void muon_norm_batch_apply(precision_t* dst,const float* norms,const MuonNormDesc* desc) {
    MuonNormDesc d=desc[blockIdx.y];if(blockIdx.x>=d.blocks)return;
    float inv_norm=1.0f/fmaxf(sqrtf(norms[blockIdx.y]),1e-7f);
    for(int i=blockIdx.x*256+threadIdx.x;i<d.n;i+=256*d.blocks)
        dst[d.offset+i]=from_float(to_float(dst[d.offset+i])*inv_norm);
}
int main(){std::vector<int> ns={1,4,24,255,256,257,768,1024,4096,65535,65536,65537,191264,1048576,3145728};std::vector<MuonNormDesc>d;long n=0;for(int x:ns){d.push_back({n,x,std::min((x+255)/256,256)});n+=x;}
precision_t *x,*y;float *pa,*pb,*na,*nb;MuonNormDesc *ds;assert(cudaMalloc(&x,n*2)==0);assert(cudaMalloc(&y,n*2)==0);cudaMalloc(&pa,d.size()*256*4);cudaMalloc(&pb,d.size()*256*4);cudaMalloc(&na,d.size()*4);cudaMalloc(&nb,d.size()*4);cudaMalloc(&ds,d.size()*sizeof(MuonNormDesc));cudaMemcpy(ds,d.data(),d.size()*sizeof(MuonNormDesc),cudaMemcpyHostToDevice);
std::vector<precision_t>h(n),aa(n),bb(n);std::vector<float>an(d.size()),bn(d.size());
for(int pat=0;pat<5;pat++){for(long i=0;i<n;i++){float v=sin(i*.13)*cos(i*.031);if(pat==0)v=0;if(pat==2&&i%11)v=0;if(pat==3)v*=1e-15;if(pat==4)v*=1e12;h[i]=__float2bfloat16(v);}cudaMemcpy(x,h.data(),n*2,cudaMemcpyHostToDevice);cudaMemcpy(y,h.data(),n*2,cudaMemcpyHostToDevice);
for(int j=0;j<d.size();j++){auto z=d[j];muon_sum_sq_partials<<<z.blocks,256>>>(pa+j*256,x+z.offset,z.n);muon_sum_sq_reduce<<<1,256>>>(na+j,pa+j*256,z.blocks);muon_l2_normalize<<<(z.n+255)/256,256>>>(x+z.offset,na+j,1e-7f,z.n);}
muon_norm_batch_partials<<<dim3(256,d.size()),256>>>(pb,y,ds);muon_norm_batch_reduce<<<d.size(),256>>>(nb,pb,ds);muon_norm_batch_apply<<<dim3(256,d.size()),256>>>(y,nb,ds);assert(cudaDeviceSynchronize()==0);cudaMemcpy(aa.data(),x,n*2,cudaMemcpyDeviceToHost);cudaMemcpy(bb.data(),y,n*2,cudaMemcpyDeviceToHost);cudaMemcpy(an.data(),na,d.size()*4,cudaMemcpyDeviceToHost);cudaMemcpy(bn.data(),nb,d.size()*4,cudaMemcpyDeviceToHost);assert(!memcmp(an.data(),bn.data(),d.size()*4));assert(!memcmp(aa.data(),bb.data(),n*2));printf("pattern=%d params=%zu elements=%ld bitwise=PASS\n",pat,d.size(),n);}}
