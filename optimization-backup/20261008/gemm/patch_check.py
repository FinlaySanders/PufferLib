from pathlib import Path
import shutil
r=Path(__file__).parent;s=r/'source';shutil.copy(r/'actual_check.cuh',s/'src/actual_check.cuh')
p=s/'src/algo.cu';t=p.read_text().replace('// Dense row-major GEMM:', '#ifdef PUF_GEMM_VALIDATE\n#include "actual_check.cuh"\n#endif\n\n// Dense row-major GEMM:',1)
t=t.replace('        return;\n    }\n#endif\n    cublasGemmEx(handle,','''#ifdef PUF_GEMM_VALIDATE
        if(beta==0) actual_gradient_check(handle,M,N,K,A,B,C,stream,alpha);
#endif
        return;
    }
#endif
    cublasGemmEx(handle,''',1)
t=t.replace('C, CUBLAS_PRECISION, N, CUBLAS_COMPUTE, CUBLAS_GEMM_DEFAULT);','''C, CUBLAS_PRECISION, N, CUBLAS_COMPUTE, CUBLAS_GEMM_DEFAULT);
#ifdef PUF_GEMM_VALIDATE
    if(USE_BF16 && op_a==CUBLAS_OP_T && op_b==CUBLAS_OP_N && M<=64 && N<=64 && K>=65536 && beta==0)
        actual_gradient_check(handle,M,N,K,A,B,C,stream,alpha);
#endif''',1);p.write_text(t)
