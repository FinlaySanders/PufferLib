from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
code='''#ifdef PUF_MUON_OUTPLACE
#include <cublasLt.h>
#include <vector>
struct OutplacePlan { int M,N,K; cublasLtMatmulDesc_t desc; cublasLtMatrixLayout_t a,b,c; cublasLtMatmulAlgo_t algo; };
thread_local cublasLtHandle_t outplace_handle=nullptr;
thread_local std::vector<OutplacePlan> outplace_plans;
static OutplacePlan& outplace_plan(int M,int N,int K) {
    for(auto& p:outplace_plans)if(p.M==M&&p.N==N&&p.K==K)return p;
    if(!outplace_handle)assert(cublasLtCreate(&outplace_handle)==CUBLAS_STATUS_SUCCESS);
    OutplacePlan p={};p.M=M;p.N=N;p.K=K;
    assert(cublasLtMatmulDescCreate(&p.desc,CUBLAS_COMPUTE_32F,CUDA_R_32F)==CUBLAS_STATUS_SUCCESS);
    assert(cublasLtMatrixLayoutCreate(&p.a,CUDA_R_16BF,N,K,N)==CUBLAS_STATUS_SUCCESS);
    assert(cublasLtMatrixLayoutCreate(&p.b,CUDA_R_16BF,K,M,K)==CUBLAS_STATUS_SUCCESS);
    assert(cublasLtMatrixLayoutCreate(&p.c,CUDA_R_16BF,N,M,N)==CUBLAS_STATUS_SUCCESS);
    cublasLtMatmulPreference_t pref;cublasLtMatmulPreferenceCreate(&pref);
    size_t workspace=32UL<<20;uint32_t reductions=CUBLASLT_REDUCTION_SCHEME_COMPUTE_TYPE;
    cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&workspace,sizeof(workspace));
    cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_REDUCTION_SCHEME_MASK,&reductions,sizeof(reductions));
    cublasLtMatmulHeuristicResult_t result;int count=0;
    assert(cublasLtMatmulAlgoGetHeuristic(outplace_handle,p.desc,p.a,p.b,p.c,p.c,pref,1,&result,&count)==CUBLAS_STATUS_SUCCESS && count==1);
    p.algo=result.algo;cublasLtMatmulPreferenceDestroy(pref);outplace_plans.push_back(p);return outplace_plans.back();
}
static void outplace_mm(Prec* A,Prec* B,Prec* C,Prec* D,cudaStream_t stream,float alpha,float beta) {
    int M=A->shape[0],K=A->shape[1],N=B->shape[1];auto& p=outplace_plan(M,N,K);
    void* workspace=nullptr;
    for(auto* ws=g_cublas_workspaces;ws;ws=ws->next)if(ws->stream==stream){workspace=ws->data;break;}
    assert(workspace);
    assert(cublasLtMatmul(outplace_handle,p.desc,&alpha,B->data,p.a,A->data,p.b,&beta,C->data,p.c,D->data,p.c,&p.algo,workspace,32UL<<20,stream)==CUBLAS_STATUS_SUCCESS);
}
#endif

'''
i=s.index('constexpr double ns_coeffs');s=s[:i]+code+s[i:]
a='''            max_N = max(max_N, max(R, C));''';assert a in s
s=s.replace(a,a+'''
#ifdef PUF_MUON_OUTPLACE
            int M=min(R,C);outplace_plan(M,M,M);
            outplace_plan(R,C,M);
#endif''',1)
a='''            puf_copy(&gram_buf, &gram, stream);
            puf_mm_nn(&gram, &gram, &gram_buf, stream,
                (float)ns_coeffs[i][2], (float)ns_coeffs[i][1]);
            puf_copy(&dst, &src, stream);
            if (tall) {
                puf_mm_nn(&src, &gram_buf, &dst,
                    stream, 1.0f, (float)ns_coeffs[i][0]);
            } else {
                puf_mm_nn(&gram_buf, &src, &dst,
                    stream, 1.0f, (float)ns_coeffs[i][0]);
            }'''
b='''#ifdef PUF_MUON_OUTPLACE
            outplace_mm(&gram,&gram,&gram,&gram_buf,stream,(float)ns_coeffs[i][2],(float)ns_coeffs[i][1]);
            if(tall)outplace_mm(&src,&gram_buf,&src,&dst,stream,1.0f,(float)ns_coeffs[i][0]);
            else outplace_mm(&gram_buf,&src,&src,&dst,stream,1.0f,(float)ns_coeffs[i][0]);
#else
'''+a+'''
#endif''';assert a in s;s=s.replace(a,b);p.write_text(s)
