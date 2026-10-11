#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <cmath>
#include <algorithm>
using precision_t=__nv_bfloat16;
#define to_float __bfloat162float
#define from_float __float2bfloat16
#define CU(x) assert((x)==cudaSuccess)
__global__ void cast(precision_t* dst,float* src,int n){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)dst[i]=from_float(src[i]);}
__global__ void muon_store_update(precision_t* __restrict__ dst,
        const precision_t* __restrict__ src, float scale, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        dst[idx] = from_float(scale * to_float(src[idx]));
    }
}

// wb = wb * (1 - lr*wd) - lr * update  (update already scaled; one call for all params)
__global__ void muon_store_apply_cast(precision_t* __restrict__ update,
        const precision_t* __restrict__ src, float* __restrict__ weights,
        precision_t* __restrict__ params, const float* __restrict__ lr_ptr,
        float scale, float wd, int n) {
    float lr = *lr_ptr;
    float wd_scale = 1.0f - lr * wd;
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        precision_t u = from_float(scale * to_float(src[i]));
        update[i] = u;
        float w = weights[i] * wd_scale - lr * to_float(u);
        weights[i] = w;
        params[i] = from_float(w);
    }
}

__global__ void muon_apply_cast(float* __restrict__ weights,
        precision_t* __restrict__ params, const precision_t* __restrict__ update,
        const float* __restrict__ lr_ptr, float wd, int n) {
    float lr = *lr_ptr;
    float wd_scale = 1.0f - lr * wd;
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        float w = weights[i] * wd_scale - lr * to_float(update[i]);
        weights[i] = w;
        params[i] = from_float(w);
    }
}

__global__ void muon_weight_update(float* __restrict__ wb,
        const precision_t* __restrict__ update,
        const float* __restrict__ lr_ptr, float wd, int n) {
    float lr = *lr_ptr;
    float wd_scale = 1.0f - lr * wd;
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        wb[idx] = wb[idx] * wd_scale - lr * to_float(update[idx]);
    }
}

int main(){
 CU(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));
 int cases=0;long long values=0;
 for(int n:{1,17,1024,65539,3145728})for(float scale:{1.0f,1.7320508f}){
 std::vector<float> w(n);std::vector<precision_t> x(n);float lr=.000724f;
 for(int i=0;i<n;i++){w[i]=((i*997LL)%8191-4095)/4096.0f;x[i]=from_float(((i*137LL)%4093-2046)/128.0f);}
 float *wa,*wb,*dc;precision_t *src,*ua,*ub,*pa,*pb;
 CU(cudaMalloc(&wa,n*4));CU(cudaMalloc(&wb,n*4));CU(cudaMalloc(&dc,4));CU(cudaMemcpy(dc,&lr,4,cudaMemcpyHostToDevice));
 CU(cudaMalloc(&src,n*2));CU(cudaMemcpy(src,x.data(),n*2,cudaMemcpyHostToDevice));
 CU(cudaMalloc(&ua,n*2));CU(cudaMalloc(&ub,n*2));CU(cudaMalloc(&pa,n*2));CU(cudaMalloc(&pb,n*2));
 CU(cudaMemcpy(wa,w.data(),n*4,cudaMemcpyHostToDevice));int grid=(n+255)/256;
 muon_store_update<<<grid,256>>>(ua,src,scale,n);muon_weight_update<<<grid,256>>>(wa,ua,dc,0,n);cast<<<grid,256>>>(pa,wa,n);CU(cudaDeviceSynchronize());
 std::vector<float> refw(n),gotw(n);std::vector<precision_t> refp(n),gotp(n),refu(n),gotu(n);
 CU(cudaMemcpy(refw.data(),wa,n*4,cudaMemcpyDeviceToHost));CU(cudaMemcpy(refp.data(),pa,n*2,cudaMemcpyDeviceToHost));CU(cudaMemcpy(refu.data(),ua,n*2,cudaMemcpyDeviceToHost));
 for(int mode=1;mode<=2;mode++){
 CU(cudaMemcpy(wb,w.data(),n*4,cudaMemcpyHostToDevice));
 if(mode==1){muon_store_update<<<grid,256>>>(ub,src,scale,n);muon_apply_cast<<<grid,256>>>(wb,pb,ub,dc,0,n);}
 else muon_store_apply_cast<<<grid,256>>>(ub,src,wb,pb,dc,scale,0,n);
 CU(cudaDeviceSynchronize());CU(cudaMemcpy(gotw.data(),wb,n*4,cudaMemcpyDeviceToHost));CU(cudaMemcpy(gotp.data(),pb,n*2,cudaMemcpyDeviceToHost));CU(cudaMemcpy(gotu.data(),ub,n*2,cudaMemcpyDeviceToHost));
 long nw=0,np=0;double err=0,norm=0,maxabs=0;
 for(int i=0;i<n;i++){nw+=refw[i]!=gotw[i];np+=memcmp(&refp[i],&gotp[i],2)!=0;assert(std::isfinite(gotw[i]));double d=(double)gotw[i]-refw[i];err+=d*d;norm+=(double)refw[i]*refw[i];maxabs=std::max(maxabs,std::abs(d));}
 double rel=std::sqrt(err/std::max(norm,1e-30));
 printf("n=%d scale=%g mode=%d master_diffs=%ld param_diffs=%ld maxabs=%.12g rel_l2=%.12g\n",n,scale,mode,nw,np,maxabs,rel);fflush(stdout);
 assert(nw==0 && np==0);assert(memcmp(refu.data(),gotu.data(),n*2)==0);cases++;values+=n;
 }
 CU(cudaFree(wa));CU(cudaFree(wb));CU(cudaFree(dc));CU(cudaFree(src));CU(cudaFree(ua));CU(cudaFree(ub));CU(cudaFree(pa));CU(cudaFree(pb));
 }
 printf("WEIGHT_CAST_SMOKE cases=%d triples=%lld update_exact=1 master_finite=1\n",cases,values);
}
