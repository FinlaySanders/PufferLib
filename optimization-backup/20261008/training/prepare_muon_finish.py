from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
a='struct Muon {'
code='''#ifdef PUF_MUON_FINISH
struct MuonFinishDesc { long offset;int n;float scale;int matrix; };
__global__ void muon_finish(float* wb,precision_t* gc,const precision_t* raw,const float* lr_ptr,
        const MuonFinishDesc* desc,const int2* tasks) {
    int2 task=tasks[blockIdx.x];MuonFinishDesc d=desc[task.x];int i=task.y*256+threadIdx.x;
    if(i>=d.n)return;long idx=d.offset+i;
    precision_t u=d.matrix?from_float(d.scale*to_float(raw[idx])):gc[idx];gc[idx]=u;
    float lr=*lr_ptr,wd_scale=1.0f-lr*0.0f;
    wb[idx]=wb[idx]*wd_scale-lr*to_float(u);
}
#endif
''';assert a in s;s=s.replace(a,code+a+'''
#ifdef PUF_MUON_FINISH
    Prec finish_x;MuonFinishDesc* finish_desc;int2* finish_tasks;int finish_count;
#endif''',1)
a='''    m->param_alloc = param_alloc;'''
b=a+'''
#ifdef PUF_MUON_FINISH
    int count=param_alloc->num_regs,total_blocks=0;long off=0;
    auto* desc=(MuonFinishDesc*)calloc(count,sizeof(MuonFinishDesc));
    for(int i=0;i<count;i++) {
        auto& e=param_alloc->regs[i];long n=numel(e.shape);int matrix=ndim(e.shape)>=2;
        float scale=matrix?sqrtf(fmaxf(1.0f,(float)e.shape[0]/(float)(n/e.shape[0]))):1.0f;
        desc[i]={off,(int)n,scale,matrix};off+=n;total_blocks+=grid_size(n);
    }
    auto* tasks=(int2*)malloc(total_blocks*sizeof(int2));int j=0;
    for(int i=0;i<count;i++)for(int b=0;b<grid_size(desc[i].n);b++)tasks[j++]=make_int2(i,b);
    m->finish_count=total_blocks;
    assert(cudaMalloc(&m->finish_desc,count*sizeof(MuonFinishDesc))==cudaSuccess);
    assert(cudaMemcpy(m->finish_desc,desc,count*sizeof(MuonFinishDesc),cudaMemcpyHostToDevice)==cudaSuccess);
    assert(cudaMalloc(&m->finish_tasks,total_blocks*sizeof(int2))==cudaSuccess);
    assert(cudaMemcpy(m->finish_tasks,tasks,total_blocks*sizeof(int2),cudaMemcpyHostToDevice)==cudaSuccess);
    free(tasks);free(desc);
    m->finish_x={.shape={param_alloc->total_elems}};alloc_register(alloc,&m->finish_x);
#endif''';assert a in s;s=s.replace(a,b,1)
a='''            Prec& dst = (i % 2 == 0) ? x_buf : x;''';assert a in s
s=s.replace(a,'''            Prec dst = (i % 2 == 0) ? x_buf : x;
#ifdef PUF_MUON_FINISH
            if(i==4)dst.data=m->finish_x.data+(gc_ptr-grads.data);
#endif''',1)
a='''        float scale = sqrtf(fmaxf(1.0f, (float)R / (float)C));
        muon_store_update<<<grid_size(ne), BLOCK_SIZE, 0, stream>>>(
            gc_ptr, x_buf.data, scale, (int)ne);''';assert a in s;s=s.replace(a,'#ifndef PUF_MUON_FINISH\n'+a+'\n#endif',1)
a='''#ifdef PUF_MUON_FUSE_CAST
    if(low)''';assert a in s;s=s.replace(a,'''#ifdef PUF_MUON_FINISH
#ifdef PUF_MUON_FUSE_CAST
#error "Finish prototype retains the standard final cast"
#endif
    muon_finish<<<m->finish_count,256,0,stream>>>(weights.data,grads.data,m->finish_x.data,m->lr,m->finish_desc,m->finish_tasks);
#else
'''+a,1)
a='''        weights.data, grads.data, m->lr, 0.0f, n_grad);''';assert a in s;s=s.replace(a,a+'\n#endif',1);p.write_text(s)
