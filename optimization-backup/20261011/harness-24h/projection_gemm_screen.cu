#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublas_v2.h>
#include <cublasLt.h>
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
 if(i<n) {uint32_t x=(uint32_t)i*1664525u+seed;x^=x>>13;p[i]=__float2bfloat16(((int)(x%257)-128)/128.0f);}
}
struct Shape { const char* name;int M,N,K;cublasOperation_t oa,ob; };
int main() {
 CU(cudaSetDeviceFlags(cudaDeviceScheduleBlockingSync));
 cudaStream_t stream;CU(cudaStreamCreateWithFlags(&stream,cudaStreamNonBlocking));
 cublasHandle_t h;BL(cublasCreate(&h));BL(cublasSetStream(h,stream));
 const size_t ws_bytes=4u<<20;void* ws;CU(cudaMalloc(&ws,ws_bytes));
 BL(cublasSetWorkspace(h,ws,ws_bytes));BL(cublasSetMathMode(h,CUBLAS_DEFAULT_MATH));
 cublasLtHandle_t lt;BL(cublasLtCreate(&lt));
 Shape shapes[]={{"projection_forward",4096,1024,1698,CUBLAS_OP_N,CUBLAS_OP_T},
 {"projection_dx",4096,1698,1024,CUBLAS_OP_N,CUBLAS_OP_N},
 {"projection_dw",1024,1698,4096,CUBLAS_OP_T,CUBLAS_OP_N}};
 printf("shape,index,algo_id,workspace,trial,microseconds,rel_l2,max_abs,finite\n");fflush(stdout);
 for(Shape s:shapes) {
  bf16 *A,*B,*C;CU(cudaMalloc(&A,(size_t)s.M*s.K*2));CU(cudaMalloc(&B,(size_t)s.K*s.N*2));CU(cudaMalloc(&C,(size_t)s.M*s.N*2));
  init_values<<<((size_t)s.M*s.K+255)/256,256,0,stream>>>(A,(size_t)s.M*s.K,713);
  init_values<<<((size_t)s.K*s.N+255)/256,256,0,stream>>>(B,(size_t)s.K*s.N,997);
  CU(cudaStreamSynchronize(stream));
  int lda=s.oa==CUBLAS_OP_N?s.K:s.M,ldb=s.ob==CUBLAS_OP_N?s.N:s.K;
  cublasLtMatmulDesc_t desc;BL(cublasLtMatmulDescCreate(&desc,CUBLAS_COMPUTE_32F,CUDA_R_32F));
  BL(cublasLtMatmulDescSetAttribute(desc,CUBLASLT_MATMUL_DESC_TRANSA,&s.ob,sizeof(s.ob)));
  BL(cublasLtMatmulDescSetAttribute(desc,CUBLASLT_MATMUL_DESC_TRANSB,&s.oa,sizeof(s.oa)));
  cublasLtMatrixLayout_t la,lb,lc;
  BL(cublasLtMatrixLayoutCreate(&la,CUDA_R_16BF,ldb,s.ob==CUBLAS_OP_N?s.K:s.N,ldb));
  BL(cublasLtMatrixLayoutCreate(&lb,CUDA_R_16BF,lda,s.oa==CUBLAS_OP_N?s.M:s.K,lda));
  BL(cublasLtMatrixLayoutCreate(&lc,CUDA_R_16BF,s.N,s.M,s.N));
  cublasLtMatmulPreference_t pref;BL(cublasLtMatmulPreferenceCreate(&pref));
  uint32_t align=16, reduction=CUBLASLT_REDUCTION_SCHEME_COMPUTE_TYPE;
  BL(cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&ws_bytes,sizeof(ws_bytes)));
  BL(cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_REDUCTION_SCHEME_MASK,&reduction,sizeof(reduction)));
  for(auto key:{CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_A_BYTES,CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_B_BYTES,CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_C_BYTES,CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_D_BYTES})
   BL(cublasLtMatmulPreferenceSetAttribute(pref,key,&align,sizeof(align)));
  cublasLtMatmulHeuristicResult_t algos[32];int count=0;
  BL(cublasLtMatmulAlgoGetHeuristic(lt,desc,la,lb,lc,lc,pref,32,algos,&count));
  fprintf(stderr,"shape=%s candidates=%d M=%d N=%d K=%d workspace_limit=%zu\n",s.name,count,s.M,s.N,s.K,ws_bytes);
  float alpha=1,beta=0;
  auto launch=[&](int index) {
   if(index<0) BL(cublasGemmEx(h,s.ob,s.oa,s.N,s.M,s.K,&alpha,B,CUDA_R_16BF,ldb,A,CUDA_R_16BF,lda,&beta,C,CUDA_R_16BF,s.N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT));
   else BL(cublasLtMatmul(lt,desc,&alpha,B,la,A,lb,&beta,C,lc,C,lc,&algos[index].algo,ws,ws_bytes,stream));
  };
  launch(-1);CU(cudaStreamSynchronize(stream));
  std::vector<bf16> reference((size_t)s.M*s.N),got(reference.size());
  CU(cudaMemcpy(reference.data(),C,reference.size()*2,cudaMemcpyDeviceToHost));
  std::vector<int> order;order.push_back(-1);for(int i=0;i<count;i++)if(algos[i].state==CUBLAS_STATUS_SUCCESS)order.push_back(i);order.push_back(-2);
  for(int index:order) {
   launch(index);CU(cudaStreamSynchronize(stream));
   CU(cudaMemcpy(got.data(),C,got.size()*2,cudaMemcpyDeviceToHost));
   double err=0,norm=0,max_abs=0;bool finite=true;
   for(size_t i=0;i<got.size();i++){double a=__bfloat162float(reference[i]),b=__bfloat162float(got[i]);finite&=std::isfinite(b);err+=(a-b)*(a-b);norm+=a*a;max_abs=std::max(max_abs,std::abs(a-b));}
   double rel=std::sqrt(err/std::max(norm,1e-30));assert(finite&&rel<0.03);
   cudaGraph_t graph;cudaGraphExec_t exec;const int repeats=64;
   CU(cudaStreamBeginCapture(stream,cudaStreamCaptureModeThreadLocal));
   for(int rep=0;rep<repeats;rep++)launch(index);
   CU(cudaStreamEndCapture(stream,&graph));CU(cudaGraphInstantiate(&exec,graph,0));
   for(int warm=0;warm<100;warm++)CU(cudaGraphLaunch(exec,stream));CU(cudaStreamSynchronize(stream));
   int id=-1;size_t written=0;
   if(index>=0)BL(cublasLtMatmulAlgoConfigGetAttribute(&algos[index].algo,CUBLASLT_ALGO_CONFIG_ID,&id,sizeof(id),&written));
   cudaEvent_t start,end;CU(cudaEventCreate(&start));CU(cudaEventCreate(&end));
   for(int trial=0;trial<5;trial++) {
    CU(cudaEventRecord(start,stream));CU(cudaGraphLaunch(exec,stream));CU(cudaEventRecord(end,stream));CU(cudaEventSynchronize(end));
    float ms=0;CU(cudaEventElapsedTime(&ms,start,end));
    printf("%s,%d,%d,%zu,%d,%.8f,%.12g,%.9g,%d\n",s.name,index,id,index<0?0:algos[index].workspaceSize,trial,ms*1000/repeats,rel,max_abs,finite);fflush(stdout);
   }
   CU(cudaEventDestroy(start));CU(cudaEventDestroy(end));CU(cudaGraphExecDestroy(exec));CU(cudaGraphDestroy(graph));
  }
  BL(cublasLtMatmulPreferenceDestroy(pref));BL(cublasLtMatrixLayoutDestroy(la));BL(cublasLtMatrixLayoutDestroy(lb));BL(cublasLtMatrixLayoutDestroy(lc));BL(cublasLtMatmulDescDestroy(desc));
  CU(cudaFree(A));CU(cudaFree(B));CU(cudaFree(C));
 }
 BL(cublasDestroy(h));BL(cublasLtDestroy(lt));CU(cudaFree(ws));CU(cudaStreamDestroy(stream));
}
