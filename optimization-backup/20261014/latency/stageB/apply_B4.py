"""Stage B4: NH_NO_SPLITK=1 — cuBLASLt inference plans (M <= 1024) with zero workspace and reduction scheme NONE (no split-K → one kernel per
matmul); the scheduler slot threads' cuBLAS handles get a zero workspace so cublasGemmEx also avoids split-K. No new kernels."""
from pathlib import Path
def rep(t,old,new,count=1):
    assert t.count(old)==count, (t.count(old), old[:90]); return t.replace(old,new)
f=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/ocean/nethack/nethack.cu'); t=f.read_text()
t=rep(t,"""        size_t workspace = 4UL << 20;
        assert(cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&workspace,sizeof(workspace)) == CUBLAS_STATUS_SUCCESS);
        cublasLtMatmulHeuristicResult_t result;""",
"""        size_t workspace = 4UL << 20;
        static int no_splitk = getenv("NH_NO_SPLITK") ? atoi(getenv("NH_NO_SPLITK")) : 0;
        if (no_splitk && M <= 1024) { /* inference-sized plans: forbid split-K so each matmul is one kernel */
            workspace = 0; uint32_t red = CUBLASLT_REDUCTION_SCHEME_NONE;
            assert(cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_REDUCTION_SCHEME_MASK,&red,sizeof(red)) == CUBLAS_STATUS_SUCCESS);
        }
        assert(cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&workspace,sizeof(workspace)) == CUBLAS_STATUS_SUCCESS);
        cublasLtMatmulHeuristicResult_t result;""")
f.write_text(t)
p=Path('/puffertank/experiments/nethack-scheduler-20261012/trainer/source/src/pufferl.cu'); t=p.read_text()
t=rep(t,"""    cudaStream_t stream = p->streams[s]; cublas_init_stream(stream);""",
"""    cudaStream_t stream = p->streams[s]; cublas_init_stream(stream);
    if (getenv("NH_NO_SPLITK") && atoi(getenv("NH_NO_SPLITK"))) cublasSetWorkspace(cublas_handle(stream), NULL, 0); /* no split-K for this slot's plain GEMMs */""")
p.write_text(t); print('B4 applied')
