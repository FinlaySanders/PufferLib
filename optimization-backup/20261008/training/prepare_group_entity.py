from pathlib import Path
r=Path(__file__).parent;p=r/'source/ocean/nethack/nethack.cu';s=p.read_text()
a='struct NethackEncoderActivations {';s=s.replace(a,a+'''
#ifdef PUF_GROUP_ENTITY
    Long group_ptrs;
#endif''',1)
for marker,allocator in [('    a->ide_idx = {.shape = {B_TT, 4}};','acts'),('    a->ide_idx = {.shape = {B, 4}};','alloc')]:
 assert marker in s;s=s.replace(marker,marker+f'\n#ifdef PUF_GROUP_ENTITY\n    a->group_ptrs={{.shape={{12}}}};alloc_register({allocator},&a->group_ptrs);\n#endif',1)
anchor='static Prec nethack_encoder_forward('
helper='''#ifdef PUF_GROUP_ENTITY
__global__ void nh_set_group_ptrs(void** p,void* w0,void* w1,void* w2,void* w3,
    void* x0,void* x1,void* x2,void* x3,void* y0,void* y1,void* y2,void* y3) {
    if(threadIdx.x==0) {p[0]=w0;p[1]=w1;p[2]=w2;p[3]=w3;p[4]=x0;p[5]=x1;p[6]=x2;p[7]=x3;p[8]=y0;p[9]=y1;p[10]=y2;p[11]=y3;}
}
static void nh_group_last(NethackEncoderWeights* ew,NethackEncoderActivations* a,int B,cudaStream_t stream) {
    static_assert(NH_MV==NH_SPM,"matching hidden width");
    void** ptrs=(void**)a->group_ptrs.data;
    nh_set_group_ptrs<<<1,32,0,stream>>>(ptrs,ew->mv2_w.data,ew->mm2_w.data,ew->im2_w.data,ew->spm2_w.data,
        a->mh1.data,a->mh1m.data,a->mh1i.data,a->sph1.data,a->mvv.data,a->mvm.data,a->mvi.data,a->spv.data);
    cublasOperation_t ta[4]={CUBLAS_OP_T,CUBLAS_OP_T,CUBLAS_OP_T,CUBLAS_OP_T},tb[4]={CUBLAS_OP_N,CUBLAS_OP_N,CUBLAS_OP_N,CUBLAS_OP_N};
    int m[4]={NH_MV,NH_MV,NH_MV,NH_MV},n[4]={B*NH_INV,B*NH_LABK,B*NH_LABK,B*NH_SPELL_SLOTS};
    int k[4]={NH_MV,NH_MV,NH_MV,NH_MV},g[4]={1,1,1,1};float alpha[4]={1,1,1,1},beta[4]={0,0,0,0};
    cublasSetStream(g_cublas_handle,stream);
    for(auto* ws=g_cublas_workspaces;ws;ws=ws->next)if(ws->stream==stream){cublasSetWorkspace(g_cublas_handle,ws->data,32UL<<20);break;}
    auto status=cublasGemmGroupedBatchedEx(g_cublas_handle,ta,tb,m,n,k,alpha,(const void* const*)ptrs,CUBLAS_PRECISION,k,
        (const void* const*)(ptrs+4),CUBLAS_PRECISION,k,beta,ptrs+8,CUBLAS_PRECISION,m,4,g,CUBLAS_COMPUTE);
    assert(status==CUBLAS_STATUS_SUCCESS);
    precision_t* values[4]={a->mvv.data,a->mvm.data,a->mvi.data,a->spv.data};
    precision_t* biases[4]={ew->mv2_b.data,ew->mm2_b.data,ew->im2_b.data,ew->spm2_b.data};
    for(int j=0;j<4;j++)nh_bias_relu_kernel<<<grid_size(n[j]*NH_MV),BLOCK_SIZE,0,stream>>>(values[j],biases[j],n[j],NH_MV);
}
#endif

'''
assert anchor in s;s=s.replace(anchor,helper+anchor,1)
# Move independent last layers/pools after all first layers. Preserve pooling and its BF16 stages.
blocks=[]
for start,end in [
('    { Prec h1f = {.data = a->mh1.data,','B NH_POOL_BIAS(ew->mv2_b.data));'),
('    { Prec h1f = {.data = a->mh1m.data,','B NH_POOL_BIAS(ew->mm2_b.data));'),
('    { Prec h1f = {.data = a->mh1i.data,','B NH_POOL_BIAS(ew->im2_b.data));'),
('    { Prec hf = {.data = a->sph1.data,','B NH_POOL_BIAS(ew->spm2_b.data));')]:
 i=s.index(start,s.index(anchor));j=s.index(end,i)+len(end);block=s[i:j];blocks.append(block[block.index('    NH_SUMMAX'):]);s=s[:i]+'#ifndef PUF_GROUP_ENTITY\n'+block+'\n#endif'+s[j:]
marker='    NH_MM_BR(&a->concat, &ew->proj_w, &a->out, ew->proj_b);'
assert marker in s;s=s.replace(marker,'#ifdef PUF_GROUP_ENTITY\n    nh_group_last(ew,a,B,stream);\n'+'\n'.join(blocks)+'\n#endif\n'+marker,1)
p.write_text(s)
