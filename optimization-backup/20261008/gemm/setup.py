from pathlib import Path
import shutil,subprocess,os
r=Path(__file__).parent;s=r/'source';shutil.copytree('/puffertank/experiments/nethack-sampler-20260917/source',s,symlinks=True)
shutil.copy(r/'split.cuh',s/'src/split.cuh')
p=s/'src/algo.cu';t=p.read_text();t=t.replace('void cublas_init_handle() {','''#ifdef PUF_SPLITK
#include "split.cuh"
thread_local float* g_split_main = nullptr;
thread_local float* g_split_dw = nullptr;
#endif
void cublas_init_handle() {
#ifdef PUF_SPLITK
    cudaMalloc(&g_split_main, 128*64*64*sizeof(float));
    cudaMalloc(&g_split_dw, 128*64*64*sizeof(float));
#endif''',1)
t=t.replace('    cublasSetStream(handle, stream);\n    cublasGemmEx(handle,', '''    cublasSetStream(handle, stream);
#ifdef PUF_GEMM_WORKSPACE
    assert(cublasSetWorkspace(handle, handle == g_cublas_dw_handle ? g_cublas_dw_workspace : g_cublas_workspace, 32*1024*1024) == CUBLAS_STATUS_SUCCESS);
#endif
#ifdef PUF_SPLITK
    if (USE_BF16 && op_a == CUBLAS_OP_T && op_b == CUBLAS_OP_N && M<=64 && N<=64 && K>=65536 && K%128==0) {
        split_mm(handle,M,N,K,A,B,C,handle==g_cublas_dw_handle?g_split_dw:g_split_main,stream,128,alpha,beta);
        return;
    }
#endif
    cublasGemmEx(handle,''',1);p.write_text(t)
for name,flags in [('baseline',''),('workspace','-DPUF_GEMM_WORKSPACE'),('split','-DPUF_SPLITK'),('both','-DPUF_GEMM_WORKSPACE -DPUF_SPLITK')]:
 print('BUILD',name,flush=True)
 with (r/f'build-{name}.log').open('w') as f:
  p=subprocess.run(['./build.sh','nethack','puffer_'+name],cwd=s,env=dict(os.environ,NVCC_EXTRA='-DPUF_ENV_WS -DPUF_PERF_LOAD -DPUF_HEAD_SAMPLER '+flags),stdout=f,stderr=subprocess.STDOUT)
 assert p.returncode==0,name
