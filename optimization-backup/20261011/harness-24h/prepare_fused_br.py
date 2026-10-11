from pathlib import Path
import difflib

root = Path(__file__).resolve().parent
source = root / 'source'
prior = root.parent / 'nethack-muon-followups-20261009/source'

def save(relative, text):
    before = (prior / relative).read_text()
    path = source / relative
    assert not path.is_symlink()
    path.write_text(text)
    patch = ''.join(difflib.unified_diff(before.splitlines(True), text.splitlines(True),
        fromfile='a/'+relative, tofile='b/'+relative))
    (root / (Path(relative).name + '.fused_br.patch')).write_text(patch)

s = (prior / 'src/algo.cu').read_text()
s = '#include <cublasLt.h>\nthread_local cublasLtHandle_t g_nh_epilogue_handle = NULL;\n' + s
old = 'void cublas_init_handle() {\n'
assert s.count(old) == 1
s = s.replace(old, old + '''    if (getenv("NH_FUSED_BR") && atoi(getenv("NH_FUSED_BR")) && !g_nh_epilogue_handle)
        assert(cublasLtCreate(&g_nh_epilogue_handle) == CUBLAS_STATUS_SUCCESS);
''')
save('src/algo.cu', s)

s = (prior / 'ocean/nethack/nethack.cu').read_text()
marker = '// GEMM + bias + relu (16 launches per forward)\n'
assert s.count(marker) == 1
helper = r'''
#include <vector>
struct NhEpiloguePlan {
    int M, N, K;
    cublasLtMatmulDesc_t desc;
    cublasLtMatrixLayout_t weights, input, output;
    cublasLtMatmulAlgo_t algo;
    bool available;
};
thread_local std::vector<NhEpiloguePlan> nh_epilogue_plans;
thread_local bool nh_fused_br_active = false;
static int nh_fused_br_mode = getenv("NH_FUSED_BR") ? atoi(getenv("NH_FUSED_BR")) : 0;

static bool nh_fused_br(Prec* input, Prec* weights, Prec* output, Prec bias, cudaStream_t stream) {
    if (!nh_fused_br_active) return false;
    int M = batch_size(input->shape) * input->shape[ndim(input->shape)-2];
    int K = input->shape[ndim(input->shape)-1];
    int N = weights->shape[ndim(weights->shape)-2];
    NhEpiloguePlan* p = NULL;
    for (NhEpiloguePlan& plan : nh_epilogue_plans)
        if (plan.M == M && plan.N == N && plan.K == K) { p = &plan; break; }
    if (!p) {
        NhEpiloguePlan plan = {};
        plan.M=M; plan.N=N; plan.K=K;
        assert(g_nh_epilogue_handle);
        assert(cublasLtMatmulDescCreate(&plan.desc, CUBLAS_COMPUTE, CUDA_R_32F) == CUBLAS_STATUS_SUCCESS);
        cublasOperation_t trans = CUBLAS_OP_T;
        cublasLtEpilogue_t epilogue = CUBLASLT_EPILOGUE_RELU_BIAS;
        assert(cublasLtMatmulDescSetAttribute(plan.desc, CUBLASLT_MATMUL_DESC_TRANSA, &trans, sizeof(trans)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatmulDescSetAttribute(plan.desc, CUBLASLT_MATMUL_DESC_EPILOGUE, &epilogue, sizeof(epilogue)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatmulDescSetAttribute(plan.desc, CUBLASLT_MATMUL_DESC_BIAS_DATA_TYPE, &CUBLAS_PRECISION, sizeof(CUBLAS_PRECISION)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatmulDescSetAttribute(plan.desc, CUBLASLT_MATMUL_DESC_BIAS_POINTER, &bias.data, sizeof(bias.data)) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&plan.weights,CUBLAS_PRECISION,K,N,K) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&plan.input,CUBLAS_PRECISION,K,M,K) == CUBLAS_STATUS_SUCCESS);
        assert(cublasLtMatrixLayoutCreate(&plan.output,CUBLAS_PRECISION,N,M,N) == CUBLAS_STATUS_SUCCESS);
        cublasLtMatmulPreference_t pref;
        assert(cublasLtMatmulPreferenceCreate(&pref) == CUBLAS_STATUS_SUCCESS);
        size_t workspace = 4UL << 20;
        assert(cublasLtMatmulPreferenceSetAttribute(pref,CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES,&workspace,sizeof(workspace)) == CUBLAS_STATUS_SUCCESS);
        cublasLtMatmulHeuristicResult_t result;
        int count=0;
        assert(cublasLtMatmulAlgoGetHeuristic(g_nh_epilogue_handle,plan.desc,plan.weights,plan.input,
            plan.output,plan.output,pref,1,&result,&count) == CUBLAS_STATUS_SUCCESS);
        plan.available = count > 0 && result.state == CUBLAS_STATUS_SUCCESS;
        if (plan.available) plan.algo=result.algo;
        cublasLtMatmulPreferenceDestroy(pref);
        fprintf(stderr,"NH_FUSED_PLAN M=%d N=%d K=%d available=%d\n",M,N,K,plan.available);
        nh_epilogue_plans.push_back(plan);
        p = &nh_epilogue_plans.back();
    }
    if (!p->available) return false;
    assert(cublasLtMatmulDescSetAttribute(p->desc,CUBLASLT_MATMUL_DESC_BIAS_POINTER,&bias.data,sizeof(bias.data)) == CUBLAS_STATUS_SUCCESS);
    void* workspace = NULL;
    for (int i=0;i<g_num_cublas_streams;i++)
        if (g_cublas_streams[i].stream==stream) { workspace=g_cublas_streams[i].workspace; break; }
    assert(workspace);
    float alpha=1.0f,beta=0.0f;
    assert(cublasLtMatmul(g_nh_epilogue_handle,p->desc,&alpha,weights->data,p->weights,
        input->data,p->input,&beta,output->data,p->output,output->data,p->output,
        &p->algo,workspace,4UL<<20,stream) == CUBLAS_STATUS_SUCCESS);
    return true;
}
'''
s = s.replace(marker, helper + '\n' + marker)
old = '''#define NH_MM_BR(A, W, O, BIAS) do { puf_mm((A), (W), (O), stream); \
    int64_t nn_ = numel((O)->shape); int dd_ = (int)(O)->shape[ndim((O)->shape) - 1]; \
    nh_bias_relu_kernel<<<grid_size(nn_), BLOCK_SIZE, 0, stream>>>((O)->data, (BIAS).data, (int)nn_, dd_); } while (0)'''
# Keep literal preprocessor continuation backslashes.
old = old.replace(';     ', '; \\\n+    ')
start = s.index('#define NH_MM_BR(')
end = s.index('// constants', start)
s = s[:start] + '''#define NH_MM_BR(A, W, O, BIAS) do { \\
    if (!nh_fused_br((A), (W), (O), (BIAS), stream)) { \\
        puf_mm((A), (W), (O), stream); \\
        int64_t nn_ = numel((O)->shape); int dd_ = (int)(O)->shape[ndim((O)->shape) - 1]; \\
        nh_bias_relu_kernel<<<grid_size(nn_), BLOCK_SIZE, 0, stream>>>((O)->data, (BIAS).data, (int)nn_, dd_); \\
    } } while (0)
''' + s[end:]
s = s.replace('struct NethackEncoderActivations {', 'struct NethackEncoderActivations {\n    bool training;')
for func, value in [('nethack_encoder_reg_train', 'true'), ('nethack_encoder_reg_rollout', 'false')]:
    start = s.index('static void ' + func)
    pos = s.index('    NethackEncoderActivations* a = (NethackEncoderActivations*)activations;', start)
    pos += len('    NethackEncoderActivations* a = (NethackEncoderActivations*)activations;')
    s = s[:pos] + '\n    a->training = ' + value + ';' + s[pos:]
start = s.index('static Prec nethack_encoder_forward')
pos = s.index('    int B = input.shape[0];', start)
s = s[:pos] + '    nh_fused_br_active = (nh_fused_br_mode & (a->training ? 2 : 1)) != 0;\n' + s[pos:]
save('ocean/nethack/nethack.cu', s)
