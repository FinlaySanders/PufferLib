from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text();a='thread_local cublasHandle_t g_cublas_handle = NULL;';assert a in s
s=s.replace(a,'''#ifdef PUF_SM_TARGET
thread_local bool puf_training_gemm=false;
static int training_sm_target(){const char* s=getenv("PUF_TRAIN_SMS");return s?atoi(s):0;}
#endif
'''+a,1)
a='''    cublasSetStream(handle, stream);''';assert a in s
s=s.replace(a,'''#ifdef PUF_SM_TARGET
    assert(cublasSetSmCountTarget(handle,puf_training_gemm?training_sm_target():0)==CUBLAS_STATUS_SUCCESS);
#endif
'''+a,1)
a='''    assert(cublasLtMatmulDescCreate(&p.desc,CUBLAS_COMPUTE_32F,CUDA_R_32F)==CUBLAS_STATUS_SUCCESS);''';assert a in s
s=s.replace(a,a+'''
#ifdef PUF_SM_TARGET
    int sm=training_sm_target();assert(cublasLtMatmulDescSetAttribute(p.desc,CUBLASLT_MATMUL_DESC_SM_COUNT_TARGET,&sm,sizeof(sm))==CUBLAS_STATUS_SUCCESS);
#endif''',1);p.write_text(s)
p=r/'source/src/pufferl.cu';s=p.read_text();a='''static void train_epoch_gpu(PuffeRL* pufferl, RolloutBuf src, int slot,
        cudaStream_t stream) {''';assert a in s
s=s.replace(a,a+'''
#ifdef PUF_SM_TARGET
    puf_training_gemm=true;
#endif''',1)
a='''    puf_stamp<<<1, 1, 0, stream>>>(st + TE_E);
}''';assert a in s
s=s.replace(a,'''#ifdef PUF_SM_TARGET
    puf_training_gemm=false;
#endif
'''+a,1);p.write_text(s)
