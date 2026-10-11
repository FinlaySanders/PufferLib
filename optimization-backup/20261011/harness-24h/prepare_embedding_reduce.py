from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'source/ocean/nethack/nethack.cu'
text = path.read_text()
assert 'embedding_reduce.cuh' not in text

def function(name):
    start = text.index('__global__ void ' + name + '(')
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

helper = '''// Isolated deterministic tree reductions; same FP32 accumulation type.
__device__ __forceinline__ float nh_embed_block_sum(float value) {
    __shared__ float partials[8];
    int lane = threadIdx.x & 31, warp = threadIdx.x >> 5;
    for (int shift = 16; shift; shift >>= 1)
        value += __shfl_down_sync(0xffffffff, value, shift);
    if (lane == 0) partials[warp] = value;
    __syncthreads();
    if (warp == 0) {
        value = lane < 8 ? partials[lane] : 0.0f;
        for (int shift = 16; shift; shift >>= 1)
            value += __shfl_down_sync(0xffffffff, value, shift);
    }
    return value;
}
static int nh_embed_reduce_bits() {
    const char* value = getenv("NH_EMBED_REDUCE");
    return value ? atoi(value) : 0;
}
'''
identity = function('nh_idemb_grad_kernel')
identity = identity.replace('nh_idemb_grad_kernel', 'nh_idemb_grad_parallel_kernel')
identity = identity.replace('int t = blockIdx.x * blockDim.x + threadIdx.x;', 'int t = blockIdx.x;')
identity = identity.replace('for (int b = 0; b < B; b++)', 'for (int b = threadIdx.x; b < B; b += blockDim.x)')
identity = identity.replace('out[row * wdt + d] = from_float(acc);',
    'acc = nh_embed_block_sum(acc);\n    if (threadIdx.x == 0) out[row * wdt + d] = from_float(acc);')

kind = function('nh_ekind_grad_kernel')
kind = kind.replace('nh_ekind_grad_kernel', 'nh_ekind_grad_parallel_kernel')
kind = kind.replace('int i = blockIdx.x * blockDim.x + threadIdx.x;', 'int i = blockIdx.x;')
kind = kind.replace('int j = nh_kind_csr_off[r]; j < nh_kind_csr_off[r + 1]; j++',
    'int j = nh_kind_csr_off[r] + threadIdx.x; j < nh_kind_csr_off[r + 1]; j += blockDim.x')
kind = kind.replace('dK[i] = from_float(acc);',
    'acc = nh_embed_block_sum(acc);\n    if (threadIdx.x == 0) dK[i] = from_float(acc);')

local = '''
// Fixed-point conversion occurs before reduction, preserving integer sums.
__global__ void nh_loc3_scatter_shared_kernel(long long* __restrict__ acc,
    const precision_t* __restrict__ dx, const float* __restrict__ crop_glyph,
    const unsigned char* __restrict__ lut, int B) {
    __shared__ unsigned long long bins[NH_LOCC_CLASSES * NH_LOCC_DIM];
    for (int i = threadIdx.x; i < NH_LOCC_CLASSES * NH_LOCC_DIM; i += blockDim.x)
        bins[i] = 0;
    __syncthreads();
    for (int t = blockIdx.x * blockDim.x + threadIdx.x;
            t < B * NH_LOC_IN; t += gridDim.x * blockDim.x) {
        int b = t / NH_LOC_IN, j = t % NH_LOC_IN;
        int p = j / NH_LOCC_DIM, d = j % NH_LOCC_DIM;
        int g = (int)crop_glyph[(int64_t)b * NH_CGRID + p];
        int cls = p == (NH_CGRID / 2) ? 7 : (int)lut[g];
        float v = to_float(dx[t]);
        if (v != 0.0f) atomicAdd(&bins[cls * NH_LOCC_DIM + d],
            (unsigned long long)(long long)__float2ll_rn(v * NH_FXP));
    }
    __syncthreads();
    for (int i = threadIdx.x; i < NH_LOCC_CLASSES * NH_LOCC_DIM; i += blockDim.x)
        if (bins[i]) atomicAdd((unsigned long long*)&acc[i], bins[i]);
}
'''
(path.parent / 'embedding_reduce.cuh').write_text(helper + identity + '\n' + kind + '\n' + local)
anchor = '\n// encoder structs\n'
assert text.count(anchor) == 1
text = text.replace(anchor, '\n#include "embedding_reduce.cuh"\n' + anchor)

start = text.index('    nh_idemb_grad_kernel<<<')
end = text.index(';', start) + 1
call = text[start:end]
new = call.replace('nh_idemb_grad_kernel<<<grid_size(', 'nh_idemb_grad_parallel_kernel<<<(')
new = new.replace('), BLOCK_SIZE, 0, stream>>>', '), 256, 0, stream>>>')
text = text[:start] + '    if (nh_embed_reduce_bits() & 1) {\n' + new + '\n    } else {\n' + call + '\n    }' + text[end:]

start = text.index('    nh_ekind_grad_kernel<<<')
end = text.index(';', start) + 1
call = text[start:end]
new = call.replace('nh_ekind_grad_kernel<<<grid_size(NH_NKIND * NH_EMBED_DIM), BLOCK_SIZE',
    'nh_ekind_grad_parallel_kernel<<<NH_NKIND * NH_EMBED_DIM, 256')
text = text[:start] + '    if (nh_embed_reduce_bits() & 2) {\n' + new + '\n    } else {\n' + call + '\n    }' + text[end:]

start = text.index('    nh_loc3_scatter_kernel<<<')
end = text.index(';', start) + 1
call = text[start:end]
new = call.replace('nh_loc3_scatter_kernel<<<grid_size((int64_t)B * NH_LOC_IN), BLOCK_SIZE',
    'nh_loc3_scatter_shared_kernel<<<256, 256')
text = text[:start] + '    if (nh_embed_reduce_bits() & 4) {\n' + new + '\n    } else {\n' + call + '\n    }' + text[end:]
path.write_text(text)
print('Prepared three separately gated embedding backward reductions.')
