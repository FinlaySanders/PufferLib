from pathlib import Path
import shutil
r=Path(__file__).parent;p=r/'source/src/algo.cu';shutil.copy(r/'lt.cuh',p.parent/'lt.cuh');s=p.read_text()
s=s.replace('void cublas_init_handle() {','''#ifdef PUF_LT_MUON
#include "lt.cuh"
thread_local cublasLtHandle_t g_lt = nullptr;
thread_local std::vector<LtPlan> g_lt_plans;
thread_local bool g_muon_active = false;
static void init_lt() {
    if(g_lt)return;
    assert(cublasLtCreate(&g_lt)==CUBLAS_STATUS_SUCCESS);
    const char*path=getenv("PUF_LT_CONFIG");assert(path);FILE*f=fopen(path,"rb");assert(f);
    LtShape s;while(fread(&s,sizeof(s),1,f)==1)g_lt_plans.push_back(lt_plan(s));assert(feof(f));fclose(f);
}
#endif
void cublas_init_handle() {
#ifdef PUF_LT_MUON
    init_lt();
#endif''',1)
s=s.replace('    int lda = (op_a == CUBLAS_OP_N) ? K : M;', '''#ifdef PUF_LT_MUON
    if(USE_BF16 && g_muon_active) {
        for(auto &p:g_lt_plans) if(p.s.M==M && p.s.N==N && p.s.K==K && p.s.oa==op_a && p.s.ob==op_b) {
            assert(lt_call(g_lt,p,A,B,C,g_cublas_workspace,stream,alpha,beta)==CUBLAS_STATUS_SUCCESS);
            return;
        }
    }
#endif
    int lda = (op_a == CUBLAS_OP_N) ? K : M;''',1)
s=s.replace('float max_grad_norm, cudaStream_t stream = 0) {\n    int n_grad','''float max_grad_norm, cudaStream_t stream = 0) {
#ifdef PUF_LT_MUON
    g_muon_active = true;
#endif
    int n_grad''',1)
s=s.replace('weights.data, grads.data, m->lr, 0.0f, n_grad);','''weights.data, grads.data, m->lr, 0.0f, n_grad);
#ifdef PUF_LT_MUON
    g_muon_active = false;
#endif''',1)
p.write_text(s)
p=r/'train.py';s=p.read_text().replace("PUF_PERF_START_WEIGHTS=ckpt)","PUF_PERF_START_WEIGHTS=ckpt,PUF_LT_CONFIG=str(r/'lt-config.bin'))");(r/'train_lt.py').write_text(s)
