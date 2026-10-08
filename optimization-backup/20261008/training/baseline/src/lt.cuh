#pragma once
#include <cublasLt.h>
#include <cublas_v2.h>
#include <vector>
#include <cstdio>
#include <cassert>
struct LtShape {int M,N,K,oa,ob;cublasLtMatmulAlgo_t algo;};
struct LtPlan {LtShape s;cublasLtMatmulDesc_t desc;cublasLtMatrixLayout_t a,b,c;};
static LtPlan lt_plan(LtShape s){
 LtPlan p;p.s=s;assert(cublasLtMatmulDescCreate(&p.desc,CUBLAS_COMPUTE_32F,CUDA_R_32F)==CUBLAS_STATUS_SUCCESS);
 cublasOperation_t opa=(cublasOperation_t)s.ob,opb=(cublasOperation_t)s.oa;
 cublasLtMatmulDescSetAttribute(p.desc,CUBLASLT_MATMUL_DESC_TRANSA,&opa,sizeof(opa));cublasLtMatmulDescSetAttribute(p.desc,CUBLASLT_MATMUL_DESC_TRANSB,&opb,sizeof(opb));
 int ar=s.ob==0?s.N:s.K,ac=s.ob==0?s.K:s.N,br=s.oa==0?s.K:s.M,bc=s.oa==0?s.M:s.K;
 cublasLtMatrixLayoutCreate(&p.a,CUDA_R_16BF,ar,ac,ar);cublasLtMatrixLayoutCreate(&p.b,CUDA_R_16BF,br,bc,br);cublasLtMatrixLayoutCreate(&p.c,CUDA_R_16BF,s.N,s.M,s.N);return p;
}
static void lt_destroy(LtPlan&p){cublasLtMatmulDescDestroy(p.desc);cublasLtMatrixLayoutDestroy(p.a);cublasLtMatrixLayoutDestroy(p.b);cublasLtMatrixLayoutDestroy(p.c);}
static cublasStatus_t lt_call(cublasLtHandle_t h,LtPlan&p,const void*A,const void*B,void*C,void*ws,cudaStream_t stream,float alpha,float beta){return cublasLtMatmul(h,p.desc,&alpha,B,p.a,A,p.b,&beta,C,p.c,C,p.c,&p.s.algo,ws,32<<20,stream);}
