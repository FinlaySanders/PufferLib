from pathlib import Path
r=Path(__file__).parent;p=r/'source/src/algo.cu';s=p.read_text()
s=s.replace('struct Muon {','''struct Muon {
#ifdef PUF_MUON_PARALLEL
    int lanes;
    cudaStream_t lane_stream[4];
    cudaEvent_t lane_start,lane_end[4];
    Prec lane_gram[4],lane_gram_buf[4],lane_x[4];
#endif''',1)
a='''    alloc_register(alloc, &m->x_buf);
}'''
b='''    alloc_register(alloc, &m->x_buf);
#ifdef PUF_MUON_PARALLEL
#ifndef PUF_MUON_BATCH_NORM
#error "Parallel Muon requires independent batched norms"
#endif
    m->lanes=getenv("PUF_MUON_LANES")?atoi(getenv("PUF_MUON_LANES")):2;
    assert(m->lanes>=1 && m->lanes<=4);
    cudaEventCreateWithFlags(&m->lane_start,cudaEventDisableTiming);
    for(int l=1;l<m->lanes;l++) {
        cudaStreamCreateWithFlags(&m->lane_stream[l],cudaStreamNonBlocking);
        cublas_register_stream(m->lane_stream[l]);
        cudaEventCreateWithFlags(&m->lane_end[l],cudaEventDisableTiming);
        m->lane_gram[l]={.shape={max_M,max_M}};
        m->lane_gram_buf[l]={.shape={max_M,max_M}};
        m->lane_x[l]={.shape={max_M,max_N}};
        alloc_register(alloc,&m->lane_gram[l]);
        alloc_register(alloc,&m->lane_gram_buf[l]);
        alloc_register(alloc,&m->lane_x[l]);
    }
#endif
}'''
assert a in s;s=s.replace(a,b,1)
a='''    // Per-param NS into workspace; write scaled update back into flat grads.'''
b='''#ifdef PUF_MUON_PARALLEL
    cudaStream_t main_stream=stream;
    cudaEventRecord(m->lane_start,main_stream);
    for(int l=1;l<m->lanes;l++)cudaStreamWaitEvent(m->lane_stream[l],m->lane_start,0);
    int matrix_number=0;
#endif
'''+a
assert a in s;s=s.replace(a,b,1)
a='''        Prec gram_buf = {.data = m->gram_buf.data, .shape = {M, M}};'''
b=a+'''
#ifdef PUF_MUON_PARALLEL
        int lane=matrix_number++%m->lanes;
        stream=lane?m->lane_stream[lane]:main_stream;
        if(lane) { x_buf.data=m->lane_x[lane].data; gram.data=m->lane_gram[lane].data; gram_buf.data=m->lane_gram_buf[lane].data; }
#endif'''
assert a in s;s=s.replace(a,b,1)
a='''#ifdef PUF_MUON_FUSE_CAST
    if(low)'''
b='''#ifdef PUF_MUON_PARALLEL
    for(int l=1;l<m->lanes;l++) {
        cudaEventRecord(m->lane_end[l],m->lane_stream[l]);
        cudaStreamWaitEvent(main_stream,m->lane_end[l],0);
    }
    stream=main_stream;
#endif
'''+a
assert a in s;s=s.replace(a,b,1);p.write_text(s)
