#include <cuda_runtime.h>
#include <cstdio>
#include <cassert>
typedef unsigned short precision_t;
__global__ void transpose_obs_wide(precision_t* dst, const precision_t* src,
        int A, int B, int C) {
    long idx = (long)blockIdx.x * blockDim.x + threadIdx.x;
    long total = (long)A * B * C;
    if (idx >= total) return;
    long a = idx / ((long)B * C);
    long rem = idx % ((long)B * C);
    long b = rem / C;
    long c = rem % C;
    dst[b * A * C + a * C + c] = src[idx];
}


__device__ unsigned short pattern(unsigned long long i){return (i*2654435761ULL+(i>>31)*97ULL)%65521;}
__global__ void fill(unsigned short* x,long n){for(long i=(long)blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=(long)gridDim.x*blockDim.x)x[i]=pattern(i);}
__global__ void check(unsigned short* x,long n,int A,int B,int C,unsigned long long* errors){for(long i=(long)blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=(long)gridDim.x*blockDim.x){long b=i/((long)A*C),a=(i/C)%A,c=i%C;long j=(a*B+b)*C+c;if(x[i]!=pattern(j))atomicAdd(errors,1ULL);}}
int main(){int A=512,B=1024,C=4600;long n=(long)A*B*C;unsigned short *x,*y;unsigned long long *e,h;assert(cudaMalloc(&x,n*2)==cudaSuccess);assert(cudaMalloc(&y,n*2)==cudaSuccess);assert(cudaMalloc(&e,8)==cudaSuccess);cudaMemset(e,0,8);fill<<<4096,256>>>(x,n);transpose_obs_wide<<<(n+255)/256,256>>>(y,x,A,B,C);assert(cudaGetLastError()==cudaSuccess);check<<<4096,256>>>(y,n,A,B,C,e);assert(cudaDeviceSynchronize()==cudaSuccess);cudaMemcpy(&h,e,8,cudaMemcpyDeviceToHost);printf("elements=%ld errors=%llu\n",n,h);assert(h==0);}
