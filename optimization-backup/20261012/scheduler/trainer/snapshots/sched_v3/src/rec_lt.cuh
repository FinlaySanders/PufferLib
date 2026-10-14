// Isolated shape-specific inference GEMM experiment. BF16 inputs/output, FP32 accumulation.
struct RecLtPlan {
    cublasLtMatmulDesc_t desc;
    cublasLtMatrixLayout_t a,b,c;
    cublasLtMatmulAlgo_t algo;
    bool ready;
};
thread_local RecLtPlan g_rec_plan = {};

static bool rec_lt_try(cublasOperation_t op_a,cublasOperation_t op_b,
        int M,int N,int K,void* A,void* B,void* C,cudaStream_t stream,float alpha,float beta) {
    const char* option=getenv("NH_REC_LT");
    if(!option || op_a!=CUBLAS_OP_N || op_b!=CUBLAS_OP_T || M!=512 || N!=3072 || K!=1024)
        return false;
    if(((uintptr_t)A|(uintptr_t)B|(uintptr_t)C)&15) return false;
    RecLtPlan& p=g_rec_plan;
    if(!p.ready) {
        assert(g_rec_lt);
        assert(cublasLtMatmulDescCreate(&p.desc,CUBLAS_COMPUTE_32F,CUDA_R_32F)==CUBLAS_STATUS_SUCCESS);
        cublasOperation_t trans=CUBLAS_OP_T;
        assert(cublasLtMatmulDescSetAttribute(p.desc,CUBLASLT_MATMUL_DESC_TRANSA,&trans,sizeof(trans))==CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&p.a,CUDA_R_16BF,K,N,K)==CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&p.b,CUDA_R_16BF,K,M,K)==CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&p.c,CUDA_R_16BF,N,M,N)==CUBLAS_STATUS_SUCCESS);
        cublasLtMatmulPreference_t pref;
        assert(cublasLtMatmulPreferenceCreate(&pref)==CUBLAS_STATUS_SUCCESS);
        size_t bytes=nh_rec_workspace_bytes();
        uint32_t alignment=16,reduction=CUBLASLT_REDUCTION_SCHEME_COMPUTE_TYPE;
        cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&bytes,sizeof(bytes));
        cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_REDUCTION_SCHEME_MASK,&reduction,sizeof(reduction));
        cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_A_BYTES,&alignment,sizeof(alignment));
        cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_B_BYTES,&alignment,sizeof(alignment));
        cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_C_BYTES,&alignment,sizeof(alignment));
        cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_D_BYTES,&alignment,sizeof(alignment));
        cublasLtMatmulHeuristicResult_t results[32];int count=0;
        assert(cublasLtMatmulAlgoGetHeuristic(g_rec_lt,p.desc,p.a,p.b,p.c,p.c,pref,32,results,&count)==CUBLAS_STATUS_SUCCESS);
        int index=atoi(option);assert(index>=0 && index<count);
        assert(results[index].state==CUBLAS_STATUS_SUCCESS);
        p.algo=results[index].algo;p.ready=true;
        fprintf(stderr,"REC_LT index=%d count=%d workspace=%zu\n",index,count,results[index].workspaceSize);
        cublasLtMatmulPreferenceDestroy(pref);
    }
    void* workspace=NULL;
    for(int i=0;i<g_num_cublas_streams;i++)if(g_cublas_streams[i].stream==stream)workspace=g_cublas_streams[i].workspace;
    assert(workspace);
    assert(cublasLtMatmul(g_rec_lt,p.desc,&alpha,B,p.a,A,p.b,&beta,C,p.c,C,p.c,
        &p.algo,workspace,nh_rec_workspace_bytes(),stream)==CUBLAS_STATUS_SUCCESS);
    return true;
}
