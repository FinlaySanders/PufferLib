#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <random>
#include <cmath>
#include <algorithm>
#include "lt.cuh"
int main(int argc,char**argv){assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);std::vector<LtPlan>plans;LtShape q;while(fread(&q,sizeof(q),1,f)==1)plans.push_back(lt_plan(q));fclose(f);
 cublasHandle_t h;cublasCreate(&h);cublasLtHandle_t lt;cublasLtCreate(&lt);void*ws;cudaMalloc(&ws,32<<20);cublasSetWorkspace(h,ws,32<<20);float coeff[5][3]={{4.0848,-6.8946,2.9270},{3.9505,-6.3029,2.6377},{3.7418,-5.5913,2.3037},{2.8769,-3.1427,1.2046},{2.8366,-3.0525,1.2012}};
 int shapes[][2]={{3072,1024},{1024,2816},{256,592},{64,16},{16,24},{64,64},{16,48},{1024,1024}};std::mt19937 rng(72);std::normal_distribution<float>normal;
 for(auto&sh:shapes)for(int pattern=0;pattern<3;pattern++){
 int R=sh[0],C=sh[1],mn=std::min(R,C),n=R*C;std::vector<__nv_bfloat16>x(n),base(n),cand(n);double norm=0;
 for(int i=0;i<n;i++){float v=normal(rng);if(pattern==1&&i%4)v=0;if(pattern==2)v=std::sin(i*.17)*std::cos(i*.31);x[i]=__float2bfloat16(v);norm+=(double)__bfloat162float(x[i])*__bfloat162float(x[i]);}
 for(auto&v:x)v=__float2bfloat16(__bfloat162float(v)/(sqrt(norm)+1e-7));
 __nv_bfloat16 *X,*Y,*G,*H;cudaMalloc(&X,n*2);cudaMalloc(&Y,n*2);cudaMalloc(&G,mn*mn*2);cudaMalloc(&H,mn*mn*2);
 for(int candidate=0;candidate<2;candidate++){
  cudaMemcpy(X,x.data(),n*2,cudaMemcpyHostToDevice);
  auto mm=[&](int M,int N,int K,int oa,int ob,void*A,void*B,void*O,float alpha,float beta){if(candidate)for(auto&p:plans)if(p.s.M==M&&p.s.N==N&&p.s.K==K&&p.s.oa==oa&&p.s.ob==ob){assert(lt_call(lt,p,A,B,O,ws,0,alpha,beta)==0);return;}int lda=oa==0?K:M,ldb=ob==0?N:K;assert(cublasGemmEx(h,(cublasOperation_t)ob,(cublasOperation_t)oa,N,M,K,&alpha,B,CUDA_R_16BF,ldb,A,CUDA_R_16BF,lda,&beta,O,CUDA_R_16BF,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT)==0);};
  for(int t=0;t<5;t++){
   auto src=t%2?Y:X,dst=t%2?X:Y;
   if(R>C)mm(C,C,R,1,0,src,src,G,1,0);else mm(R,R,C,0,1,src,src,G,1,0);
   cudaMemcpyAsync(H,G,mn*mn*2,cudaMemcpyDeviceToDevice);mm(mn,mn,mn,0,0,G,G,H,coeff[t][2],coeff[t][1]);cudaMemcpyAsync(dst,src,n*2,cudaMemcpyDeviceToDevice);
   if(R>C)mm(R,C,C,0,0,src,H,dst,1,coeff[t][0]);else mm(R,C,R,0,0,H,src,dst,1,coeff[t][0]);
  }
  cudaMemcpy((candidate?cand:base).data(),Y,n*2,cudaMemcpyDeviceToHost);
 }
 double e=0,b2=0,c2=0,dot=0;for(int i=0;i<n;i++){double b=__bfloat162float(base[i]),c=__bfloat162float(cand[i]);e+=(b-c)*(b-c);b2+=b*b;c2+=c*c;dot+=b*c;}double rel=sqrt(e/b2),cos=dot/sqrt(b2*c2);printf("MUONCHECK R=%d C=%d pattern=%d rel=%.9g cosine=%.9g\n",R,C,pattern,rel,cos);fflush(stdout);assert(std::isfinite(rel)&&rel<.03&&cos>.9995);
 cudaFree(X);cudaFree(Y);cudaFree(G);cudaFree(H);
 }
}
