// Isolated BF16 recurrent weight-gradient algorithm experiment; default off.
struct TrainDwLtPlan {
    cublasLtMatmulDesc_t desc;
    cublasLtMatrixLayout_t a, b, c;
    cublasLtMatmulAlgo_t algo;
    bool ready;
};
thread_local TrainDwLtPlan g_train_dw_plan = {};

static bool train_dw_lt_try(cublasOperation_t op_a, cublasOperation_t op_b,
        int M, int N, int K, void* A, void* B, void* C,
        cudaStream_t stream, float alpha, float beta) {
    const char* option = getenv("NH_TRAIN_DW_LT");
    if (!option || CUBLAS_PRECISION != CUDA_R_16BF ||
        op_a != CUBLAS_OP_T || op_b != CUBLAS_OP_N ||
        M != 3072 || N != 1024 || K != 4096 || alpha != 1 || beta != 0)
        return false;
    if (((uintptr_t)A | (uintptr_t)B | (uintptr_t)C) & 15) return false;
    const size_t bytes = 4u << 20;
    TrainDwLtPlan& p = g_train_dw_plan;
    if (!p.ready) {
        assert(g_rec_lt);
        assert(cublasLtMatmulDescCreate(&p.desc, CUBLAS_COMPUTE_32F, CUDA_R_32F) == CUBLAS_STATUS_SUCCESS);
        cublasOperation_t trans = CUBLAS_OP_T;
        assert(cublasLtMatmulDescSetAttribute(p.desc, CUBLASLT_MATMUL_DESC_TRANSB, &trans, sizeof(trans)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&p.a, CUDA_R_16BF, N, K, N) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&p.b, CUDA_R_16BF, M, K, M) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&p.c, CUDA_R_16BF, N, M, N) == CUBLAS_STATUS_SUCCESS);
        cublasLtMatmulPreference_t pref;
        assert(cublasLtMatmulPreferenceCreate(&pref) == CUBLAS_STATUS_SUCCESS);
        uint32_t alignment = 16, reduction = CUBLASLT_REDUCTION_SCHEME_COMPUTE_TYPE;
        assert(cublasLtMatmulPreferenceSetAttribute(pref, CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES, &bytes, sizeof(bytes)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatmulPreferenceSetAttribute(pref, CUBLASLT_MATMUL_PREF_REDUCTION_SCHEME_MASK, &reduction, sizeof(reduction)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatmulPreferenceSetAttribute(pref, CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_A_BYTES, &alignment, sizeof(alignment)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatmulPreferenceSetAttribute(pref, CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_B_BYTES, &alignment, sizeof(alignment)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatmulPreferenceSetAttribute(pref, CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_C_BYTES, &alignment, sizeof(alignment)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatmulPreferenceSetAttribute(pref, CUBLASLT_MATMUL_PREF_MIN_ALIGNMENT_D_BYTES, &alignment, sizeof(alignment)) == CUBLAS_STATUS_SUCCESS);
        cublasLtMatmulHeuristicResult_t results[32]; int count = 0;
        assert(cublasLtMatmulAlgoGetHeuristic(g_rec_lt, p.desc, p.a, p.b, p.c, p.c, pref, 32, results, &count) == CUBLAS_STATUS_SUCCESS);
        int index = atoi(option);
        assert(index >= 0 && index < count && results[index].state == CUBLAS_STATUS_SUCCESS);
        p.algo = results[index].algo;
        int id = -1; size_t written = 0;
        assert(cublasLtMatmulAlgoConfigGetAttribute(&p.algo, CUBLASLT_ALGO_CONFIG_ID, &id, sizeof(id), &written) == CUBLAS_STATUS_SUCCESS);
        assert(id == 30 && results[index].workspaceSize == 0);
        fprintf(stderr, "TRAIN_DW_LT index=%d count=%d id=%d workspace=%zu\n", index, count, id, results[index].workspaceSize);
        assert(cublasLtMatmulPreferenceDestroy(pref) == CUBLAS_STATUS_SUCCESS);
        p.ready = true;
    }
    void* workspace = NULL;
    for (int i = 0; i < g_num_cublas_streams; i++)
        if (g_cublas_streams[i].stream == stream) workspace = g_cublas_streams[i].workspace;
    assert(workspace);
    assert(cublasLtMatmul(g_rec_lt, p.desc, &alpha, B, p.a, A, p.b, &beta,
        C, p.c, C, p.c, &p.algo, workspace, bytes, stream) == CUBLAS_STATUS_SUCCESS);
    return true;
}
