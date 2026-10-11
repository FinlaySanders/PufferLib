from pathlib import Path
import re,json,hashlib,difflib
r=Path(__file__).resolve().parent
p=r/'source/ocean/nethack/nethack.cu';old=p.read_text();s=old
assert 'NH_BIAS_DIRECT' not in s
pattern=r'nh_relu_bias_bwd_kernel<<<nh_colsum_grid\([^\n]+?stream>>>\(\s*(.*?)\);'
hits=list(re.finditer(pattern,s,re.S));assert len(hits)==13,len(hits)
s=re.sub(pattern,lambda m:'nh_relu_bias_backward('+m.group(1)+', stream);',s,flags=re.S)
needle='// bias-grad column sums without a relu mask (NH_ENT_LINPOOL: linear last entity layer)'
kernel='''// Exact wide-column path: each CTA thread owns a distinct column.
__global__ void nh_relu_bias_bwd_direct_kernel(
    precision_t* __restrict__ grad, const precision_t* __restrict__ out,
    long long* __restrict__ bias_acc, int64_t total, int dim) {
    int64_t i0 = (int64_t)blockIdx.x * blockDim.x + threadIdx.x;
    int64_t stride = (int64_t)gridDim.x * blockDim.x;
    float acc = 0.0f;
    for (int64_t i = i0; i < total; i += stride) {
        float g = to_float(out[i]) > 0.0f ? to_float(grad[i]) : 0.0f;
        grad[i] = from_float(g);
        acc += g;
    }
    if (acc != 0.0f) nh_fxp_atomic_add(&bias_acc[(int)(i0 % dim)], acc);
}

'''
assert s.count(needle)==1;s=s.replace(needle,kernel+needle)
needle='// Cast the packed fixed-point bias accumulators to their grad tensors in one launch.'
wrapper='''static void nh_relu_bias_backward(precision_t* grad, const precision_t* out,
    long long* bias_acc, int64_t total, int dim, cudaStream_t stream) {
    static thread_local int direct = -1;
    if (direct < 0) direct = getenv("NH_BIAS_DIRECT") ? atoi(getenv("NH_BIAS_DIRECT")) : 0;
    assert(direct == 0 || direct == 1);
    int blocks = nh_colsum_grid(total, dim);
    if (direct && dim >= BLOCK_SIZE) {
        nh_relu_bias_bwd_direct_kernel<<<blocks, BLOCK_SIZE, 0, stream>>>(
            grad, out, bias_acc, total, dim);
    } else {
        nh_relu_bias_bwd_kernel<<<blocks, BLOCK_SIZE, dim * sizeof(long long), stream>>>(
            grad, out, bias_acc, total, dim);
    }
}

'''
assert s.count(needle)==1;s=s.replace(needle,wrapper+needle)
p.write_text(s)
(r/'BIAS_DIRECT.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/ocean/nethack/nethack.cu',tofile='after/ocean/nethack/nethack.cu')))
(r/'BIAS_DIRECT_SOURCE.json').write_text(json.dumps(dict(hypothesis='Fast-stack trace has88.27ms/226updates in fused ReLU+bias backward. For dim>=blockSize, CTA threads have distinct columns, so shared accumulator initialization, two barriers and shared staging are redundant.',method='Keep identical grid, per-thread FP32 accumulation order, BF16 masks/stores, and fixed-point quantization. Wide columns add their quantized value directly to global bias accumulator; narrow columns unchanged. No new precision or rounding intended.',gate='Extract actual kernels for synthetic exactness smoke, then interleaved saved-batch GPU timing. Full pipeline only if useful timing.',literal_launch_sites_replaced=len(hits),sha256=hashlib.sha256(s.encode()).hexdigest()),indent=2))
base=json.loads((r/'PRIORITY_CANDIDATE.json').read_text())['environment']
jobs=[]
for name,extra in [('base_a',{}),('direct',{'NH_BIAS_DIRECT':1}),('base_b',{})]:
 jobs.append(dict(kind='time',label='bias_direct_gpu_'+name,binary='bias_direct_v26',env=dict(base,**extra),args=['--trials=4']))
(r/'BIAS_DIRECT_GPU.json').write_text(json.dumps(jobs,indent=2))
print('Prepared wide bias reduction, not built;13 literal sites routed, unchanged narrow paths.')
