#include <cuda_runtime.h>
#include <cstdio>
#include <vector>
#include <random>
#include <cmath>
#include <algorithm>
#include "split.cuh"
__global__ void cvt(const __nv_bfloat16* x,float*y,int n){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)y[i]=__bfloat162float(x[i]);}
int main(){
 cublasHandle_t h;cublasCreate(&h);void*ws;cudaMalloc(&ws,32<<20);cublasSetWorkspace(h,ws,32<<20);
 int shapes[][3]={{16,24,225280},{64,64,225280},{16,16,225280},{64,16,225280},{64,64,65536},{16,48,65536},{64,16,65536},{16,16,98304},{64,64,98304}};
 std::mt19937 gen(777);std::normal_distribution<float> normal;
 for(auto &sh:shapes){int M=sh[0],N=sh[1],K=sh[2],na=M*K,nb=N*K,nc=M*N;
  std::vector<__nv_bfloat16>a(na),b(nb),out(nc);for(auto&v:a)v=__float2bfloat16(normal(gen));for(auto&v:b)v=__float2bfloat16(normal(gen));
  __nv_bfloat16 *A,*B,*C;float *AF,*BF,*R,*tmp;cudaMalloc(&A,na*2);cudaMalloc(&B,nb*2);cudaMalloc(&C,nc*2);cudaMalloc(&AF,na*4);cudaMalloc(&BF,nb*4);cudaMalloc(&R,nc*4);cudaMalloc(&tmp,nc*128*4);
  cudaMemcpy(A,a.data(),na*2,cudaMemcpyHostToDevice);cudaMemcpy(B,b.data(),nb*2,cudaMemcpyHostToDevice);cvt<<<(na+255)/256,256>>>(A,AF,na);cvt<<<(nb+255)/256,256>>>(B,BF,nb);
  float one=1,zero=0;assert(cublasGemmEx(h,CUBLAS_OP_N,CUBLAS_OP_T,N,M,K,&one,BF,CUDA_R_32F,N,AF,CUDA_R_32F,M,&zero,R,CUDA_R_32F,N,CUBLAS_COMPUTE_32F_PEDANTIC,CUBLAS_GEMM_DEFAULT)==CUBLAS_STATUS_SUCCESS);
  std::vector<float>ref(nc);cudaMemcpy(ref.data(),R,nc*4,cudaMemcpyDeviceToHost);
  // Check the independent FP32 reference against FP64 accumulation on eight outputs.
  for(int t=0;t<8;t++){int row=t*M/8,col=(t*7)%N;double sum=0;for(int k=0;k<K;k++)sum+=(double)__bfloat162float(a[k*M+row])*__bfloat162float(b[k*N+col]);assert(fabs(sum-ref[row*N+col])<0.02+fabs(sum)*0.0001);}
  for(int parts: {0,8,16,32,64,128}){
   auto call=[&](){if(parts)split_mm(h,M,N,K,A,B,C,tmp,0,parts);else assert(cublasGemmEx(h,CUBLAS_OP_N,CUBLAS_OP_T,N,M,K,&one,B,CUDA_R_16BF,N,A,CUDA_R_16BF,M,&zero,C,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT)==CUBLAS_STATUS_SUCCESS);};
   call();cudaMemcpy(out.data(),C,nc*2,cudaMemcpyDeviceToHost);double err=0,norm=0,mx=0;for(int i=0;i<nc;i++){double e=__bfloat162float(out[i])-ref[i];err+=e*e;norm+=(double)ref[i]*ref[i];mx=fmax(mx,fabs(e));}double rel=sqrt(err/norm),maxr=mx/sqrt(norm/nc);assert(rel<.003&&maxr<.016);
   // Event timing of a repeated graph keeps host-launch overhead out of the comparison.
   cudaStream_t st;cudaStreamCreate(&st);cublasSetStream(h,st);cudaStreamBeginCapture(st,cudaStreamCaptureModeGlobal);
   for(int i=0;i<10;i++){if(parts)split_mm(h,M,N,K,A,B,C,tmp,st,parts);else cublasGemmEx(h,CUBLAS_OP_N,CUBLAS_OP_T,N,M,K,&one,B,CUDA_R_16BF,N,A,CUDA_R_16BF,M,&zero,C,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT);}
   cudaGraph_t g;assert(cudaStreamEndCapture(st,&g)==cudaSuccess);cudaGraphExec_t ex;assert(cudaGraphInstantiate(&ex,g,0)==cudaSuccess);for(int j=0;j<3;j++)cudaGraphLaunch(ex,st);cudaEvent_t s,e;cudaEventCreate(&s);cudaEventCreate(&e);cudaEventRecord(s,st);for(int j=0;j<10;j++)cudaGraphLaunch(ex,st);cudaEventRecord(e,st);cudaEventSynchronize(e);float ms;cudaEventElapsedTime(&ms,s,e);
   printf("%d,%d,%d,%d,%.5f,%.8f,%.8f\n",M,N,K,parts,ms*10,rel,maxr);fflush(stdout);
   cudaGraphExecDestroy(ex);cudaGraphDestroy(g);cudaEventDestroy(s);cudaEventDestroy(e);cudaStreamDestroy(st);cublasSetStream(h,0);
  }
  cudaFree(A);cudaFree(B);cudaFree(C);cudaFree(AF);cudaFree(BF);cudaFree(R);cudaFree(tmp);
 }
}
