from pathlib import Path
import hashlib
import json

r=Path(__file__).resolve().parent
p=r/'source/src/algo.cu'
s=p.read_text();before=hashlib.sha256(p.read_bytes()).hexdigest()
assert 'MuonFusedDesc' not in s
kernels=r'''
// Experimental BF16-only small-matrix Newton-Schulz fusion. Each CTA owns
// one complete matrix and preserves every BF16 intermediate and all5steps.
#include <mma.h>
#include <type_traits>
struct MuonFusedDesc { long offset; int R, C; };
__device__ __constant__ float muon_fused_coeffs[5][3] = {
    {4.0848f,-6.8946f,2.9270f}, {3.9505f,-6.3029f,2.6377f},
    {3.7418f,-5.5913f,2.3037f}, {2.8769f,-3.1427f,1.2046f},
    {2.8366f,-3.0525f,1.2012f}
};
template<bool TRANS_B>
__device__ void muon_small_mm(const __nv_bfloat16* A,
        const __nv_bfloat16* B, __nv_bfloat16* C,
        const __nv_bfloat16* add, int M, int N, int K,
        float alpha, float beta, float* scratch) {
    using namespace nvcuda;
    int warp=threadIdx.x/32, lane=threadIdx.x%32;
    int tiles=(M/16)*(N/16);
    for(int tile=warp;tile<tiles;tile+=blockDim.x/32) {
        int row=tile/(N/16)*16, col=tile%(N/16)*16;
        wmma::fragment<wmma::matrix_a,16,16,16,__nv_bfloat16,wmma::row_major> a;
        wmma::fragment<wmma::accumulator,16,16,16,float> acc;
        wmma::fill_fragment(acc,0.0f);
        for(int k=0;k<K;k+=16) {
            wmma::load_matrix_sync(a,A+row*64+k,64);
            if constexpr(TRANS_B) {
                wmma::fragment<wmma::matrix_b,16,16,16,__nv_bfloat16,wmma::col_major> b;
                wmma::load_matrix_sync(b,B+col*64+k,64);
                wmma::mma_sync(acc,a,b,acc);
            } else {
                wmma::fragment<wmma::matrix_b,16,16,16,__nv_bfloat16,wmma::row_major> b;
                wmma::load_matrix_sync(b,B+k*64+col,64);
                wmma::mma_sync(acc,a,b,acc);
            }
        }
        float* out=scratch+warp*256;
        wmma::store_matrix_sync(out,acc,16,wmma::mem_row_major);
        __syncwarp();
        for(int j=lane;j<256;j+=32) {
            int off=(row+j/16)*64+col+j%16;
            float value=alpha*out[j];
            if(add) value+=beta*__bfloat162float(add[off]);
            C[off]=__float2bfloat16(value);
        }
        __syncwarp();
    }
    __syncthreads();
}
__global__ void muon_fused_small(__nv_bfloat16* grads,const MuonFusedDesc* desc) {
    MuonFusedDesc d=desc[blockIdx.x];
    int M=min(d.R,d.C),N=max(d.R,d.C);
    int PM=(M+15)/16*16,PN=(N+15)/16*16;
    __shared__ __align__(32) __nv_bfloat16 sm[4*64*64];
    __shared__ __align__(32) float scratch[8*256];
    __nv_bfloat16 *x=sm,*y=sm+4096,*gram=sm+8192,*gram2=sm+12288;
    for(int off=threadIdx.x;off<4096;off+=blockDim.x) {
        int row=off/64,col=off%64;
        float value=0.0f;
        if(row<M && col<N) {
            int index=d.R>d.C ? col*d.C+row : row*d.C+col;
            value=__bfloat162float(grads[d.offset+index]);
        }
        x[off]=__float2bfloat16(value);
    }
    __syncthreads();
    for(int step=0;step<5;step++) {
        muon_small_mm<true>(x,x,gram,NULL,PM,PM,PN,1.0f,0.0f,scratch);
        muon_small_mm<false>(gram,gram,gram2,gram,PM,PM,PM,
            muon_fused_coeffs[step][2],muon_fused_coeffs[step][1],scratch);
        muon_small_mm<false>(gram2,x,y,x,PM,PN,PM,
            1.0f,muon_fused_coeffs[step][0],scratch);
        __nv_bfloat16* tmp=x;x=y;y=tmp;
    }
    float scale=sqrtf(fmaxf(1.0f,(float)d.R/(float)d.C));
    for(int i=threadIdx.x;i<d.R*d.C;i+=blockDim.x) {
        int row=i/d.C,col=i%d.C;
        int off=d.R>d.C ? col*64+row : row*64+col;
        grads[d.offset+i]=__float2bfloat16(scale*__bfloat162float(x[off]));
    }
}
'''
needle='struct MuonBatch {'
assert s.count(needle)==1
s=s.replace(needle,kernels+'\n'+needle)
needle='struct Muon {\n'
s=s.replace(needle,needle+'''    MuonFusedDesc* fused_desc = NULL;
    int fused_count = 0;
    std::vector<unsigned char> fused_selected;
''',1)
needle='    m->param_alloc = param_alloc;'
init=r'''    if (const char* option=getenv("PUF_MUON_FUSED_SMALL")) {
        static_assert(std::is_same<precision_t,__nv_bfloat16>::value,
            "The isolated fused Muon experiment requires BF16");
        int limit=atoi(option);
        assert(limit==32 || limit==64);
        std::vector<MuonFusedDesc> selected;
        m->fused_selected.resize(param_alloc->num_regs,0);
        long offset=0;
        for(int i=0;i<param_alloc->num_regs;i++) {
            AllocEntry& e=param_alloc->regs[i];long n=numel(e.shape);
            if(ndim(e.shape)>=2) {
                int R=e.shape[0],C=n/R;
                if(R<=limit && C<=limit) {
                    selected.push_back({offset,R,C});m->fused_selected[i]=1;
                }
            }
            offset+=n;
        }
        m->fused_count=selected.size();
        assert(m->fused_count>0);
        assert(cudaMalloc(&m->fused_desc,selected.size()*sizeof(MuonFusedDesc))==cudaSuccess);
        assert(cudaMemcpy(m->fused_desc,selected.data(),selected.size()*sizeof(MuonFusedDesc),cudaMemcpyHostToDevice)==cudaSuccess);
        fprintf(stderr,"MUON_FUSED_SMALL count=%d limit=%d\n",m->fused_count,limit);
    }
'''
assert s.count(needle)==1;s=s.replace(needle,init+needle)
needle='    // Per-param NS into workspace; write scaled update back into flat grads.'
launch=r'''    if(m->fused_count) {
        muon_fused_small<<<m->fused_count,256,0,stream>>>(grads.data,m->fused_desc);
    }
'''
assert s.count(needle)==1;s=s.replace(needle,launch+needle)
needle='        if(m->batch_matrices) {\n            MuonBatch* group=m->groups[m->group_id[_i]];'
assert s.count(needle)==1
s=s.replace(needle,'        if(m->fused_count && m->fused_selected[_i]) continue;\n\n'+needle)
p.write_text(s)
(r/'muon_fused_small_kernels.cu.txt').write_text(kernels)
(r/'MUON_FUSED_SOURCE.json').write_text(json.dumps(dict(before_sha256=before,
    after_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),limits=[32,64],
    shared_bytes_per_cta=40960,
    hypothesis='One CTA per small matrix retains five NS iterations and BF16 intermediates in shared memory, removes intermediate kernel launches/copies. Global clipping, normalization, momentum and final weight update unchanged.',
    caveats=['BF16-only isolated prototype.','WMMA reduction order and epilogue contraction may differ.','No compiled/timing/validation result yet.']),indent=2))
print('Prepared fused-small-Muon; compile deferred during active timing.')
