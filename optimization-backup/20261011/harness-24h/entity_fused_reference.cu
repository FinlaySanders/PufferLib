#include <cuda_runtime.h>
#include <cuda_bf16.h>
#include <cublasLt.h>
#include <cassert>
#include <cstdint>
using precision_t=__nv_bfloat16;
__device__ float to_float(precision_t x){return __bfloat162float(x);}
__device__ precision_t from_float(float x){return __float2bfloat16(x);}
constexpr int NH_MV=64,NH_CONCAT=1698;
__global__ void nh_min_summax_kernel(precision_t* __restrict__ concat,
    float* __restrict__ amax, const precision_t* __restrict__ v,
    const float* __restrict__ vid, float eps, int n, int padv, int off, int B) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= B * NH_MV) return;
    int b = t / NH_MV, d = t % NH_MV;
    float sm = 0.0f, mx = -1e30f;
    int bm = -1;
    for (int k = 0; k < n; k++) {
        float id = vid[(int64_t)b * n + k];
        int bad = padv >= 0 ? ((int)id == padv) : (id < 0.0f);
        if (bad) continue;
        float vv = to_float(v[((int64_t)b * n + k) * NH_MV + d]);
        sm += vv;
        if (vv > mx) { mx = vv; bm = k; }
    }
    amax[t] = (float)bm;
    precision_t* dst = concat + (int64_t)b * NH_CONCAT + off;
    dst[d] = from_float(sm * eps);
    dst[NH_MV + d] = from_float(bm >= 0 ? mx : 0.0f);
}

struct Plan { cublasLtMatmulDesc_t d; cublasLtMatrixLayout_t w,x,y; cublasLtMatmulAlgo_t algo; };
static cublasLtHandle_t lt;
static void* workspace;
static cudaStream_t stream;
static Plan p1,p2;
static int gn,go,gp;static float ge;
static void init_plan(Plan& p,int m,int k,void* bias) {
 const int n=64;
 assert(cublasLtMatmulDescCreate(&p.d,CUBLAS_COMPUTE_32F,CUDA_R_32F)==CUBLAS_STATUS_SUCCESS);
 cublasOperation_t trans=CUBLAS_OP_T;
 cublasLtEpilogue_t epilogue=CUBLASLT_EPILOGUE_RELU_BIAS;
 cudaDataType_t dtype=CUDA_R_16BF;
 assert(cublasLtMatmulDescSetAttribute(p.d,CUBLASLT_MATMUL_DESC_TRANSA,&trans,sizeof(trans))==CUBLAS_STATUS_SUCCESS);
 assert(cublasLtMatmulDescSetAttribute(p.d,CUBLASLT_MATMUL_DESC_EPILOGUE,&epilogue,sizeof(epilogue))==CUBLAS_STATUS_SUCCESS);
 assert(cublasLtMatmulDescSetAttribute(p.d,CUBLASLT_MATMUL_DESC_BIAS_DATA_TYPE,&dtype,sizeof(dtype))==CUBLAS_STATUS_SUCCESS);
 assert(cublasLtMatmulDescSetAttribute(p.d,CUBLASLT_MATMUL_DESC_BIAS_POINTER,&bias,sizeof(bias))==CUBLAS_STATUS_SUCCESS);
 assert(cublasLtMatrixLayoutCreate(&p.w,CUDA_R_16BF,k,n,k)==CUBLAS_STATUS_SUCCESS);
 assert(cublasLtMatrixLayoutCreate(&p.x,CUDA_R_16BF,k,m,k)==CUBLAS_STATUS_SUCCESS);
 assert(cublasLtMatrixLayoutCreate(&p.y,CUDA_R_16BF,n,m,n)==CUBLAS_STATUS_SUCCESS);
 cublasLtMatmulPreference_t pref;assert(cublasLtMatmulPreferenceCreate(&pref)==CUBLAS_STATUS_SUCCESS);
 size_t bytes=4u<<20;assert(cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&bytes,sizeof(bytes))==CUBLAS_STATUS_SUCCESS);
 cublasLtMatmulHeuristicResult_t result;int count=0;
 assert(cublasLtMatmulAlgoGetHeuristic(lt,p.d,p.w,p.x,p.y,p.y,pref,1,&result,&count)==CUBLAS_STATUS_SUCCESS && count==1);
 assert(result.state==CUBLAS_STATUS_SUCCESS);p.algo=result.algo;
 cublasLtMatmulPreferenceDestroy(pref);
}
extern "C" void inv_init(void* st,void* b1,void* b2,int batch,int n,int off,int pad,float eps) {
 gn=n;go=off;gp=pad;ge=eps;
 stream=(cudaStream_t)st;
 assert(cublasLtCreate(&lt)==CUBLAS_STATUS_SUCCESS);assert(cudaMalloc(&workspace,4u<<20)==cudaSuccess);
 init_plan(p1,batch*n,16,b1);init_plan(p2,batch*n,64,b2);
}
static void mm(Plan& p,void* x,void* w,void* y) {
 float alpha=1,beta=0;
 assert(cublasLtMatmul(lt,p.d,&alpha,w,p.w,x,p.x,&beta,y,p.y,y,p.y,&p.algo,workspace,4u<<20,stream)==CUBLAS_STATUS_SUCCESS);
}
extern "C" void inv_run(void* x,void* w1,void* w2,void* h,void* v,void* gid,void* concat,void* amax,int batch) {
 mm(p1,x,w1,h);mm(p2,h,w2,v);
 nh_min_summax_kernel<<<(batch*64+255)/256,256,0,stream>>>((precision_t*)concat,(float*)amax,(precision_t*)v,(float*)gid,ge,gn,gp,go,batch);
 assert(cudaPeekAtLastError()==cudaSuccess);
}
