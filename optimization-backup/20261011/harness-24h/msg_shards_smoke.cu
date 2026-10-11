#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <vector>
using precision_t=__nv_bfloat16;
#define to_float __bfloat162float
#define from_float __float2bfloat16
#define CU(x) assert((x)==cudaSuccess)
static constexpr int NH_MSG_LEN=128,NH_MSG_HID=256,NH_MSG_VOCAB=1024,NH_CONCAT=384,NH_MSG_CONCAT_OFF=32;
static constexpr float NH_FXP=16777216.0f;
__device__ __forceinline__ void nh_fxp_atomic_add(long long* addr,float v){atomicAdd((unsigned long long*)addr,(unsigned long long)(long long)__float2ll_rn(v*NH_FXP));}
__device__ __forceinline__ float nh_fxp_to_float(long long v){return(float)((double)v*(1.0/16777216.0));}
__global__ void nh_msg_bwd_kernel(
    long long* __restrict__ dmsg_acc, const precision_t* __restrict__ grad_concat,
    const float* __restrict__ ids, int B) {
    int b = blockIdx.x;
    if (b >= B) return;
    int d = threadIdx.x;
    const float* mi = ids + (int64_t)b * NH_MSG_LEN;
    int count = 0;
    for (int t = 0; t < NH_MSG_LEN; t++) {
        if ((int)mi[t] < 0) break;
        count++;
    }
    float g = to_float(grad_concat[(int64_t)b * NH_CONCAT + NH_MSG_CONCAT_OFF + d])
              * rsqrtf((float)count + 1.0f);
    if (g == 0.0f) return;
    for (int t = 0; t < count; t++)
        nh_fxp_atomic_add(&dmsg_acc[(int64_t)(int)mi[t] * NH_MSG_HID + d], g);
}

static int nh_msg_grad_shards() {
    static int shards = getenv("NH_MSG_SHARDS") ? atoi(getenv("NH_MSG_SHARDS")) : 1;
    assert(shards >= 1 && shards <= 16 && (shards & (shards - 1)) == 0);
    return shards;
}

__global__ void nh_msg_bwd_shards_kernel(
    long long* __restrict__ acc, const precision_t* __restrict__ grad_concat,
    const float* __restrict__ ids, int B, int shards) {
    int b = blockIdx.x;
    if (b >= B) return;
    int d = threadIdx.x;
    const float* mi = ids + (int64_t)b * NH_MSG_LEN;
    int count = 0;
    for (int t = 0; t < NH_MSG_LEN; t++) {
        if ((int)mi[t] < 0) break;
        count++;
    }
    float g = to_float(grad_concat[(int64_t)b * NH_CONCAT + NH_MSG_CONCAT_OFF + d])
        * rsqrtf((float)count + 1.0f);
    if (g == 0.0f) return;
    long long q = __float2ll_rn(g * NH_FXP);
    int64_t base = (int64_t)(b & (shards - 1)) * NH_MSG_VOCAB * NH_MSG_HID;
    for (int t = 0; t < count; t++)
        atomicAdd((unsigned long long*)&acc[base + (int64_t)(int)mi[t] * NH_MSG_HID + d],
            (unsigned long long)q);
}

__global__ void nh_msg_reduce_shards_kernel(precision_t* __restrict__ out,
        const long long* __restrict__ acc, int shards) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    const int n = NH_MSG_VOCAB * NH_MSG_HID;
    if (i >= n) return;
    unsigned long long sum = 0;
    for (int s = 0; s < shards; s++) sum += (unsigned long long)acc[(int64_t)s * n + i];
    out[i] = from_float(nh_fxp_to_float((long long)sum));
}

int main(){
 CU(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));
 const size_t n=NH_MSG_VOCAB*NH_MSG_HID;int cases=0;long long values=0;
 for(int B:{1,17,512,4096})for(int mode=0;mode<4;mode++){
 std::vector<float> ids(B*NH_MSG_LEN,-1);std::vector<precision_t> grad(B*NH_CONCAT);
 for(int b=0;b<B;b++){
 int count=mode==0?0:mode==1?126:(b*13+17)%127;
 for(int t=0;t<count;t++)ids[b*NH_MSG_LEN+t]=mode==1?7:mode==2?(t+b)%8:(t*127+b*239)%NH_MSG_VOCAB;
 for(int d=0;d<NH_CONCAT;d++)grad[b*NH_CONCAT+d]=from_float(((b*997+d*137)%4093-2046)/1024.0f);
 }
 float* di;precision_t *dg,*out;long long *base,*sharded;
 CU(cudaMalloc(&di,ids.size()*4));CU(cudaMalloc(&dg,grad.size()*2));CU(cudaMalloc(&out,n*2));
 CU(cudaMalloc(&base,n*8));CU(cudaMalloc(&sharded,n*8*16));
 CU(cudaMemcpy(di,ids.data(),ids.size()*4,cudaMemcpyHostToDevice));CU(cudaMemcpy(dg,grad.data(),grad.size()*2,cudaMemcpyHostToDevice));
 CU(cudaMemset(base,0,n*8));nh_msg_bwd_kernel<<<B,NH_MSG_HID>>>(base,dg,di,B);CU(cudaDeviceSynchronize());
 std::vector<long long> reference(n);CU(cudaMemcpy(reference.data(),base,n*8,cudaMemcpyDeviceToHost));
 nh_msg_reduce_shards_kernel<<<(n+255)/256,256>>>(out,base,1);CU(cudaDeviceSynchronize());
 std::vector<precision_t> ref_out(n),got(n);CU(cudaMemcpy(ref_out.data(),out,n*2,cudaMemcpyDeviceToHost));
 for(int shards:{2,4,8,16}){
 CU(cudaMemset(sharded,0,n*8*shards));nh_msg_bwd_shards_kernel<<<B,NH_MSG_HID>>>(sharded,dg,di,B,shards);
 nh_msg_reduce_shards_kernel<<<(n+255)/256,256>>>(out,sharded,shards);CU(cudaDeviceSynchronize());
 std::vector<unsigned long long> h(n*shards);CU(cudaMemcpy(h.data(),sharded,n*shards*8,cudaMemcpyDeviceToHost));
 for(size_t i=0;i<n;i++){unsigned long long sum=0;for(int s=0;s<shards;s++)sum+=h[s*n+i];assert(sum==(unsigned long long)reference[i]);}
 CU(cudaMemcpy(got.data(),out,n*2,cudaMemcpyDeviceToHost));assert(memcmp(ref_out.data(),got.data(),n*2)==0);cases++;values+=n;
 }
 CU(cudaFree(di));CU(cudaFree(dg));CU(cudaFree(out));CU(cudaFree(base));CU(cudaFree(sharded));
 }
 printf("MSG_SHARDS_SMOKE cases=%d accumulator_and_bf16_values=%lld exact=1\n",cases,values);
}
