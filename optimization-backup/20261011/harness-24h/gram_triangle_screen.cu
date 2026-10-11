#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublas_v2.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cmath>
#include <algorithm>
#include <vector>
using bf16=__nv_bfloat16;
#define CU(x) assert((x)==cudaSuccess)
#define BL(x) assert((x)==CUBLAS_STATUS_SUCCESS)
__global__ void init_values(bf16* p,size_t n,uint32_t seed) {
 size_t i=(size_t)blockIdx.x*blockDim.x+threadIdx.x;
 if(i<n){uint32_t x=(uint32_t)i*1664525u+seed;x^=x>>13;p[i]=__float2bfloat16(((int)(x%257)-128)/128.0f);}
}
__global__ void mirror_blocks(bf16* g,int N,int block) {
 int t=blockIdx.x*blockDim.x+threadIdx.x;if(t>=N*N)return;
 int i=t/N,j=t%N;if(i/block>j/block)g[t]=g[j*N+i];
}
int main(){
 CU(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));
 cudaStream_t stream;CU(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
 cublasHandle_t h;BL(cublasCreate(&h));BL(cublasSetStream(h,stream));
 void* ws;CU(cudaMalloc(&ws,4u<<20));BL(cublasSetWorkspace(h,ws,4u<<20));BL(cublasSetMathMode(h,CUBLAS_DEFAULT_MATH));
 const int N=1024,K=3072;bf16 *x,*g;CU(cudaMalloc(&x,(size_t)N*K*2));CU(cudaMalloc(&g,(size_t)N*N*2));
 init_values<<<((size_t)N*K+255)/256,256,0,stream>>>(x,(size_t)N*K,713);CU(cudaStreamSynchronize(stream));
 float alpha=1,beta=0;
 auto baseline=[&](){BL(cublasGemmEx(h,CUBLAS_OP_N,CUBLAS_OP_T,N,N,K,&alpha,x,CUDA_R_16BF,N,x,CUDA_R_16BF,N,&beta,g,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT));};
 baseline();CU(cudaStreamSynchronize(stream));std::vector<bf16> ref((size_t)N*N),got(ref.size());CU(cudaMemcpy(ref.data(),g,ref.size()*2,cudaMemcpyDeviceToHost));
 printf("parts,trial,microseconds,rel_l2,max_abs,finite,blocks\n");fflush(stdout);
 for(int parts:{0,2,4,8,-1}){
  int tile=parts>0?N/parts:0;std::vector<bf16*> a,b,c;bf16 **da=nullptr,**db=nullptr,**dc=nullptr;
  if(parts>0){
   for(int i=0;i<parts;i++)for(int j=i;j<parts;j++){a.push_back(x+j*tile);b.push_back(x+i*tile);c.push_back(g+(size_t)i*tile*N+j*tile);}
   size_t bytes=a.size()*sizeof(bf16*);CU(cudaMalloc(&da,bytes));CU(cudaMalloc(&db,bytes));CU(cudaMalloc(&dc,bytes));
   CU(cudaMemcpy(da,a.data(),bytes,cudaMemcpyHostToDevice));CU(cudaMemcpy(db,b.data(),bytes,cudaMemcpyHostToDevice));CU(cudaMemcpy(dc,c.data(),bytes,cudaMemcpyHostToDevice));
  }
  auto launch=[&](){
   if(parts<1)baseline();else{
    BL(cublasGemmBatchedEx(h,CUBLAS_OP_N,CUBLAS_OP_T,tile,tile,K,&alpha,(const void*const*)da,CUDA_R_16BF,N,(const void*const*)db,CUDA_R_16BF,N,&beta,(void*const*)dc,CUDA_R_16BF,N,a.size(),CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT));
    mirror_blocks<<<(N*N+255)/256,256,0,stream>>>(g,N,tile);
   }
  };
  CU(cudaMemsetAsync(g,0,N*N*2,stream));launch();CU(cudaStreamSynchronize(stream));CU(cudaMemcpy(got.data(),g,got.size()*2,cudaMemcpyDeviceToHost));
  double err=0,norm=0,maxabs=0;bool finite=true;for(size_t i=0;i<got.size();i++){double v=__bfloat162float(ref[i]),w=__bfloat162float(got[i]);finite&=std::isfinite(w);err+=(v-w)*(v-w);norm+=v*v;maxabs=std::max(maxabs,std::abs(v-w));}
  double rel=std::sqrt(err/std::max(norm,1e-30));assert(finite&&rel<.03);
  cudaGraph_t graph;cudaGraphExec_t exec;const int repeats=64;
  CU(cudaStreamBeginCapture(stream,cudaStreamCaptureModeThreadLocal));for(int i=0;i<repeats;i++)launch();CU(cudaStreamEndCapture(stream,&graph));CU(cudaGraphInstantiate(&exec,graph,0));
  for(int i=0;i<10;i++)CU(cudaGraphLaunch(exec,stream));CU(cudaStreamSynchronize(stream));
  cudaEvent_t begin,end;CU(cudaEventCreate(&begin));CU(cudaEventCreate(&end));
  for(int t=0;t<5;t++){CU(cudaEventRecord(begin,stream));CU(cudaGraphLaunch(exec,stream));CU(cudaEventRecord(end,stream));CU(cudaEventSynchronize(end));float ms;CU(cudaEventElapsedTime(&ms,begin,end));printf("%d,%d,%.9f,%.12g,%.9g,%d,%zu\n",parts,t,ms*1000/repeats,rel,maxabs,finite,a.size());fflush(stdout);}
  CU(cudaEventDestroy(begin));CU(cudaEventDestroy(end));CU(cudaGraphExecDestroy(exec));CU(cudaGraphDestroy(graph));
  if(parts>0){CU(cudaFree(da));CU(cudaFree(db));CU(cudaFree(dc));}
 }
 CU(cudaFree(x));CU(cudaFree(g));BL(cublasDestroy(h));CU(cudaFree(ws));CU(cudaStreamDestroy(stream));
}
