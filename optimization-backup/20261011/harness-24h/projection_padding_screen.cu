#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublas_v2.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cmath>
#include <vector>
#include <algorithm>
using bf16=__nv_bfloat16;
#define CU(x) assert((x)==cudaSuccess)
#define BL(x) assert((x)==CUBLAS_STATUS_SUCCESS)
__global__ void init_values(bf16* p,size_t n,uint32_t seed) {
 size_t i=(size_t)blockIdx.x*blockDim.x+threadIdx.x;
 if(i<n){uint32_t x=(uint32_t)i*1664525u+seed;x^=x>>13;p[i]=__float2bfloat16(((int)(x%257)-128)/128.0f);}
}
__global__ void repack(bf16* dst,const bf16* src,int rows,int in,int out) {
 int i=blockIdx.x*blockDim.x+threadIdx.x;
 if(i<rows*out){int row=i/out,col=i%out;dst[i]=col<in?src[row*in+col]:__float2bfloat16(0.0f);}
}
struct Shape {const char* name;int M,N,K; cublasOperation_t oa,ob;};
int main(){
 CU(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));
 cudaStream_t stream;CU(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
 cublasHandle_t h;BL(cublasCreate(&h));BL(cublasSetStream(h,stream));void* ws;CU(cudaMalloc(&ws,4u<<20));BL(cublasSetWorkspace(h,ws,4u<<20));BL(cublasSetMathMode(h,CUBLAS_DEFAULT_MATH));
 Shape shapes[]={{"inference",512,1024,1698,CUBLAS_OP_N,CUBLAS_OP_T},{"forward",4096,1024,1698,CUBLAS_OP_N,CUBLAS_OP_T},{"dx",4096,1698,1024,CUBLAS_OP_N,CUBLAS_OP_N},{"dw",1024,1698,4096,CUBLAS_OP_T,CUBLAS_OP_N}};
 printf("shape,pad,moves,trial,microseconds,rel_l2,max_abs,finite\n");fflush(stdout);
 for(Shape s:shapes){
  bf16 *A,*B,*C,*Ap,*Bp,*Cp;size_t na=(size_t)s.M*s.K,nb=(size_t)s.K*s.N,nc=(size_t)s.M*s.N;
  CU(cudaMalloc(&A,na*2));CU(cudaMalloc(&B,nb*2));CU(cudaMalloc(&C,nc*2));CU(cudaMalloc(&Ap,na*4));CU(cudaMalloc(&Bp,nb*4));CU(cudaMalloc(&Cp,nc*4));
  init_values<<<(na+255)/256,256,0,stream>>>(A,na,713);init_values<<<(nb+255)/256,256,0,stream>>>(B,nb,997);CU(cudaStreamSynchronize(stream));
  float alpha=1,beta=0;
  auto gemm=[&](int M,int N,int K,bf16* aa,bf16* bb,bf16* cc){int lda=s.oa==CUBLAS_OP_N?K:M,ldb=s.ob==CUBLAS_OP_N?N:K;BL(cublasGemmEx(h,s.ob,s.oa,N,M,K,&alpha,bb,CUDA_R_16BF,ldb,aa,CUDA_R_16BF,lda,&beta,cc,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT));};
  gemm(s.M,s.N,s.K,A,B,C);CU(cudaStreamSynchronize(stream));std::vector<bf16> ref(nc),got(nc);CU(cudaMemcpy(ref.data(),C,nc*2,cudaMemcpyDeviceToHost));
  for(int pad:{0,1704,1712,1728,1792,-1})for(int moves=0;moves<=(pad>0?1:0);moves++){
   auto pack=[&](){
    if(s.K==1698){repack<<<((size_t)s.M*pad+255)/256,256,0,stream>>>(Ap,A,s.M,s.K,pad);repack<<<((size_t)s.N*pad+255)/256,256,0,stream>>>(Bp,B,s.N,s.K,pad);}
    else repack<<<((size_t)s.K*pad+255)/256,256,0,stream>>>(Bp,B,s.K,s.N,pad);
   };
   auto multiply=[&](){
    if(s.K==1698)gemm(s.M,s.N,pad,Ap,Bp,C);
    else gemm(s.M,pad,s.K,A,Bp,Cp);
   };
   auto unpack=[&](){if(s.N==1698)repack<<<((size_t)s.M*s.N+255)/256,256,0,stream>>>(C,Cp,s.M,pad,s.N);};
   auto launch=[&](){if(pad<1)gemm(s.M,s.N,s.K,A,B,C);else{if(moves)pack();multiply();if(moves)unpack();}};
   if(pad>0)pack();launch();if(pad>0&&!moves)unpack();CU(cudaStreamSynchronize(stream));CU(cudaMemcpy(got.data(),C,nc*2,cudaMemcpyDeviceToHost));
   double err=0,norm=0,maxabs=0;bool finite=true;for(size_t i=0;i<nc;i++){double a=__bfloat162float(ref[i]),b=__bfloat162float(got[i]);finite&=std::isfinite(b);err+=(a-b)*(a-b);norm+=a*a;maxabs=std::max(maxabs,std::abs(a-b));}double rel=std::sqrt(err/std::max(norm,1e-30));assert(finite&&rel<.03);
   cudaGraph_t graph;cudaGraphExec_t exec;const int repeats=64;CU(cudaStreamBeginCapture(stream,cudaStreamCaptureModeThreadLocal));for(int i=0;i<repeats;i++)launch();CU(cudaStreamEndCapture(stream,&graph));CU(cudaGraphInstantiate(&exec,graph,0));
   for(int i=0;i<200;i++)CU(cudaGraphLaunch(exec,stream));CU(cudaStreamSynchronize(stream));
   cudaEvent_t start,end;CU(cudaEventCreate(&start));CU(cudaEventCreate(&end));
   for(int trial=0;trial<5;trial++){CU(cudaEventRecord(start,stream));CU(cudaGraphLaunch(exec,stream));CU(cudaEventRecord(end,stream));CU(cudaEventSynchronize(end));float ms;CU(cudaEventElapsedTime(&ms,start,end));printf("%s,%d,%d,%d,%.9f,%.12g,%.9g,%d\n",s.name,pad,moves,trial,ms*1000/repeats,rel,maxabs,finite);fflush(stdout);}
   CU(cudaEventDestroy(start));CU(cudaEventDestroy(end));CU(cudaGraphExecDestroy(exec));CU(cudaGraphDestroy(graph));
  }
  CU(cudaFree(A));CU(cudaFree(B));CU(cudaFree(C));CU(cudaFree(Ap));CU(cudaFree(Bp));CU(cudaFree(Cp));
 }
 BL(cublasDestroy(h));CU(cudaFree(ws));CU(cudaStreamDestroy(stream));
}
