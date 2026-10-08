from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text();(r/'algo.baseline.cu').write_text(s)
anchor='constexpr double ns_coeffs[5][3] = {'
k='''#ifdef PUF_MUON_BATCH_NORM
struct MuonNormDesc { long offset; int n, blocks; };
__global__ void muon_norm_batch_partials(float* partials, const precision_t* src, const MuonNormDesc* desc) {
    MuonNormDesc d=desc[blockIdx.y];
    if (blockIdx.x >= d.blocks) return;
    __shared__ float sdata[256];
    int tid=threadIdx.x;float sum=0.0f;
    for(int i=blockIdx.x*256+tid;i<d.n;i+=256*d.blocks) { float v=to_float(src[d.offset+i]);sum+=v*v; }
    sdata[tid]=sum;
    block_reduce_sum(sdata,&partials[blockIdx.y*256+blockIdx.x],tid,256,1);
}
__global__ void muon_norm_batch_reduce(float* out,const float* partials,const MuonNormDesc* desc) {
    __shared__ float sdata[256];int tid=threadIdx.x;
    sdata[tid]=tid<desc[blockIdx.x].blocks?partials[blockIdx.x*256+tid]:0.0f;
    block_reduce_sum(sdata,&out[blockIdx.x],tid,256,1);
}
__global__ void muon_norm_batch_apply(precision_t* dst,const float* norms,const MuonNormDesc* desc) {
    MuonNormDesc d=desc[blockIdx.y];if(blockIdx.x>=d.blocks)return;
    float inv_norm=1.0f/fmaxf(sqrtf(norms[blockIdx.y]),1e-7f);
    for(int i=blockIdx.x*256+threadIdx.x;i<d.n;i+=256*d.blocks)
        dst[d.offset+i]=from_float(to_float(dst[d.offset+i])*inv_norm);
}
#endif

'''
s=s.replace(anchor,k+anchor)
s=s.replace('struct Muon {','''struct Muon {
#ifdef PUF_MUON_BATCH_NORM
    MuonNormDesc* norm_desc;
    float *batch_partials,*batch_norms;
    int norm_count;
#endif''')
a='    m->momentum = momentum;'
s=s.replace(a,a+'''
#ifdef PUF_MUON_BATCH_NORM
    MuonNormDesc* host=(MuonNormDesc*)calloc(param_alloc->num_regs,sizeof(MuonNormDesc));
    long norm_offset=0;int norm_count=0;
    for(int i=0;i<param_alloc->num_regs;i++) {
        auto& e=param_alloc->regs[i];long n=numel(e.shape);
        if(ndim(e.shape)>=2)host[norm_count++]={norm_offset,(int)n,min((int)grid_size(n),256)};
        norm_offset+=n;
    }
    m->norm_count=norm_count;
    assert(cudaMalloc(&m->norm_desc,norm_count*sizeof(MuonNormDesc))==cudaSuccess);
    assert(cudaMalloc(&m->batch_partials,norm_count*256*sizeof(float))==cudaSuccess);
    assert(cudaMalloc(&m->batch_norms,norm_count*sizeof(float))==cudaSuccess);
    assert(cudaMemcpy(m->norm_desc,host,norm_count*sizeof(MuonNormDesc),cudaMemcpyHostToDevice)==cudaSuccess);
    free(host);
#endif''')
a='    // Per-param NS into workspace; write scaled update back into flat grads.'
s=s.replace(a,'''#ifdef PUF_MUON_BATCH_NORM
    muon_norm_batch_partials<<<dim3(256,m->norm_count),256,0,stream>>>(m->batch_partials,grads.data,m->norm_desc);
    muon_norm_batch_reduce<<<m->norm_count,256,0,stream>>>(m->batch_norms,m->batch_partials,m->norm_desc);
    muon_norm_batch_apply<<<dim3(256,m->norm_count),256,0,stream>>>(grads.data,m->batch_norms,m->norm_desc);
#endif
'''+a)
a='        int nblk = min((int)grid_size(ne), 256);';b='        // 5 steps land in x_buf. 4 = you break it.'
i=s.index(a);j=s.index(b,i);s=s[:i]+'#ifndef PUF_MUON_BATCH_NORM\n'+s[i:j]+'#endif\n\n'+s[j:]
p.write_text(s)
