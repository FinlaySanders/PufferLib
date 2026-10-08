from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
for name in ('partials','apply'):
 start=s.index('__global__ void muon_norm_batch_'+name+'(');end=s.index('\n}',start)+2;part=s[start:end]
 part=part.replace('const MuonNormDesc* desc) {','''const MuonNormDesc* desc
#ifdef PUF_COMPACT_NORM
    ,const int2* tasks
#endif
    ) {
#ifdef PUF_COMPACT_NORM
    int param=tasks[blockIdx.x].x,block=tasks[blockIdx.x].y;
#else
    int param=blockIdx.y,block=blockIdx.x;
#endif''')
 # Only replace after declarations.
 split=part.index('    MuonNormDesc d=');part=part[:split]+part[split:].replace('blockIdx.y','param').replace('blockIdx.x','block')
 s=s[:start]+part+s[end:]
s=s.replace('    int norm_count;','''    int norm_count;
#ifdef PUF_COMPACT_NORM
    int2* norm_tasks;int task_count;
#endif''',1)
a='''    free(host);
#endif
    m->param_alloc'''
b='''#ifdef PUF_COMPACT_NORM
    int count=0;for(int i=0;i<norm_count;i++)count+=host[i].blocks;
    int2* tasks=(int2*)malloc(count*sizeof(int2));int j=0;
    for(int i=0;i<norm_count;i++)for(int b=0;b<host[i].blocks;b++)tasks[j++]=make_int2(i,b);
    m->task_count=count;assert(cudaMalloc(&m->norm_tasks,count*sizeof(int2))==cudaSuccess);
    assert(cudaMemcpy(m->norm_tasks,tasks,count*sizeof(int2),cudaMemcpyHostToDevice)==cudaSuccess);free(tasks);
#endif
    free(host);
#endif
    m->param_alloc'''
assert a in s;s=s.replace(a,b,1)
a='''    muon_norm_batch_partials<<<dim3(256,m->norm_count),256,0,stream>>>(m->batch_partials,grads.data,m->norm_desc);
    muon_norm_batch_reduce<<<m->norm_count,256,0,stream>>>(m->batch_norms,m->batch_partials,m->norm_desc);
    muon_norm_batch_apply<<<dim3(256,m->norm_count),256,0,stream>>>(grads.data,m->batch_norms,m->norm_desc);'''
b='''#ifdef PUF_COMPACT_NORM
    muon_norm_batch_partials<<<m->task_count,256,0,stream>>>(m->batch_partials,grads.data,m->norm_desc,m->norm_tasks);
    muon_norm_batch_reduce<<<m->norm_count,256,0,stream>>>(m->batch_norms,m->batch_partials,m->norm_desc);
    muon_norm_batch_apply<<<m->task_count,256,0,stream>>>(grads.data,m->batch_norms,m->norm_desc,m->norm_tasks);
#else
'''+a+'\n#endif';assert a in s;s=s.replace(a,b,1);p.write_text(s)
