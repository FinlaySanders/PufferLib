#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <random>
#include <cmath>
#include <algorithm>
#include "lt.cuh"
__global__ void cvtlt(const __nv_bfloat16*x,float*y,int n){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)y[i]=__bfloat162float(x[i]);}
int main(int argc,char**argv){
 assert(argc==3);FILE*in=fopen(argv[1],"r"),*out=fopen(argv[2],"wb");assert(in&&out);cublasHandle_t h;cublasCreate(&h);cublasLtHandle_t lt;cublasLtCreate(&lt);void*ws;cudaMalloc(&ws,32<<20);cudaStream_t st;cudaStreamCreate(&st);cublasSetStream(h,st);cublasSetWorkspace(h,ws,32<<20);
 std::mt19937 rng(912);std::normal_distribution<float>normal;LtShape s;
 while(fscanf(in,"%d %d %d %d %d",&s.M,&s.N,&s.K,&s.oa,&s.ob)==5){
  int M=s.M,N=s.N,K=s.K,na=M*K,nb=N*K,nc=M*N;LtPlan p=lt_plan(s);
  std::vector<__nv_bfloat16>a(na),b(nb),c(nc),got(nc);for(auto&v:a)v=__float2bfloat16(normal(rng)*.1f);for(auto&v:b)v=__float2bfloat16(normal(rng)*.1f);for(auto&v:c)v=__float2bfloat16(normal(rng)*.1f);
  __nv_bfloat16*A,*B,*C;float *AF,*BF,*R;cudaMalloc(&A,na*2);cudaMalloc(&B,nb*2);cudaMalloc(&C,nc*2);cudaMalloc(&AF,na*4);cudaMalloc(&BF,nb*4);cudaMalloc(&R,nc*4);cudaMemcpy(A,a.data(),na*2,cudaMemcpyHostToDevice);cudaMemcpy(B,b.data(),nb*2,cudaMemcpyHostToDevice);cudaMemcpy(C,c.data(),nc*2,cudaMemcpyHostToDevice);
  cvtlt<<<(na+255)/256,256,0,st>>>(A,AF,na);cvtlt<<<(nb+255)/256,256,0,st>>>(B,BF,nb);cvtlt<<<(nc+255)/256,256,0,st>>>(C,R,nc);
  float alpha=.75f,beta=s.oa==0&&s.ob==0?.5f:0;int lda=s.oa==0?K:M,ldb=s.ob==0?N:K;
  assert(cublasGemmEx(h,(cublasOperation_t)s.ob,(cublasOperation_t)s.oa,N,M,K,&alpha,BF,CUDA_R_32F,ldb,AF,CUDA_R_32F,lda,&beta,R,CUDA_R_32F,N,CUBLAS_COMPUTE_32F_PEDANTIC,CUBLAS_GEMM_DEFAULT)==0);cudaStreamSynchronize(st);std::vector<float>ref(nc);cudaMemcpy(ref.data(),R,nc*4,cudaMemcpyDeviceToHost);
  cublasLtMatmulPreference_t pref;cublasLtMatmulPreferenceCreate(&pref);size_t w=32<<20;cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&w,sizeof(w));cublasLtMatmulHeuristicResult_t hs[64];int count=0;assert(cublasLtMatmulAlgoGetHeuristic(lt,p.desc,p.a,p.b,p.c,p.c,pref,64,hs,&count)==0);
  float baseline=0,best=1e20;double besterr=0;int besti=-1;
  for(int i=-1;i<count;i++){
   if(i>=0&&hs[i].state!=CUBLAS_STATUS_SUCCESS)continue;if(i>=0)p.s.algo=hs[i].algo;
   auto call=[&](){if(i==-1)return cublasGemmEx(h,(cublasOperation_t)s.ob,(cublasOperation_t)s.oa,N,M,K,&alpha,B,CUDA_R_16BF,ldb,A,CUDA_R_16BF,lda,&beta,C,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT);return lt_call(lt,p,A,B,C,ws,st,alpha,beta);};
   cudaMemcpyAsync(C,c.data(),nc*2,cudaMemcpyHostToDevice,st);auto status=call();if(status!=0){printf("REJECT status %d\n",status);continue;}cudaStreamSynchronize(st);cudaMemcpy(got.data(),C,nc*2,cudaMemcpyDeviceToHost);double err=0,norm=0,mx=0;for(int j=0;j<nc;j++){double e=__bfloat162float(got[j])-ref[j];err+=e*e;norm+=(double)ref[j]*ref[j];mx=fmax(mx,fabs(e));}double rel=sqrt(err/norm),maxr=mx/sqrt(norm/nc);if(!(rel<.004&&maxr<.04)){printf("REJECT numeric %d %.8f %.8f\n",i,rel,maxr);continue;}
   cudaStreamBeginCapture(st,cudaStreamCaptureModeGlobal);for(int j=0;j<5;j++)assert(call()==0);cudaGraph_t g;assert(cudaStreamEndCapture(st,&g)==cudaSuccess);cudaGraphExec_t ex;assert(cudaGraphInstantiate(&ex,g,0)==cudaSuccess);cudaGraphLaunch(ex,st);cudaEvent_t beg,end;cudaEventCreate(&beg);cudaEventCreate(&end);cudaEventRecord(beg,st);for(int j=0;j<4;j++)cudaGraphLaunch(ex,st);cudaEventRecord(end,st);cudaEventSynchronize(end);float ms;cudaEventElapsedTime(&ms,beg,end);float us=ms*1000/20;
   if(i==-1)baseline=us;else if(us<best){best=us;besti=i;besterr=rel;}
   cudaGraphExecDestroy(ex);cudaGraphDestroy(g);cudaEventDestroy(beg);cudaEventDestroy(end);
  }
  bool keep=besti>=0&&best<baseline*.95;
  printf("SHAPE,%d,%d,%d,%d,%d,%.6f,%.6f,%d,%.8f,%d\n",M,N,K,s.oa,s.ob,baseline,best,besti,besterr,keep);fflush(stdout);
  if(keep){s.algo=hs[besti].algo;assert(fwrite(&s,sizeof(s),1,out)==1);fflush(out);}
  lt_destroy(p);cublasLtMatmulPreferenceDestroy(pref);cudaFree(A);cudaFree(B);cudaFree(C);cudaFree(AF);cudaFree(BF);cudaFree(R);
 }
 fclose(out);fclose(in);
}
