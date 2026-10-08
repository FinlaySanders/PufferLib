from pathlib import Path
r=Path(__file__).parent;p=r/'source/ocean/nethack/nethack.cu';s=p.read_text()
a='// table grads: one thread per (row, dim), fixed batch loop -- deterministic'
b='''#ifdef PUF_ID_ROWS
__global__ void nh_identity_rows(float* rows,const float* idx,int B) {
    int cat=threadIdx.x;if(cat>=23)return;
    int comp=cat<13?0:cat<18?1:cat<20?2:3;
    int row=cat-(comp==0?0:comp==1?13:comp==2?18:20);
    int n=0;
    for(int b=0;b<B;b++)if((int)idx[4*b+comp]==row)rows[cat*(B+1)+1+n++]=(float)b;
    rows[cat*(B+1)]=(float)n;
}
#endif
'''+a
assert a in s;s=s.replace(a,b,1)
a='''    const float* __restrict__ idx, int B) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    const int n_role'''
b='''    const float* __restrict__ idx, int B
#ifdef PUF_ID_ROWS
    ,const float* rows
#endif
    ) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    const int n_role'''
assert a in s;s=s.replace(a,b,1)
a='''    for (int b = 0; b < B; b++) {
        if ((int)idx[b * 4 + comp] != row) continue;
        acc += to_float(grad_concat[(int64_t)b * NH_CONCAT + NH_IDE_CONCAT_OFF + off + d]);
    }'''
b='''#ifdef PUF_ID_ROWS
    int cat=row+(comp==0?0:comp==1?13:comp==2?18:20);
    int count=(int)rows[cat*(B+1)];
    for(int j=0;j<count;j++) {
        int b=(int)rows[cat*(B+1)+1+j];
        acc += to_float(grad_concat[(int64_t)b * NH_CONCAT + NH_IDE_CONCAT_OFF + off + d]);
    }
#else
'''+a+'''
#endif'''
assert a in s;s=s.replace(a,b,1)
s=s.replace('    Float ide_idx; // per-sample','''#ifdef PUF_ID_ROWS
    Float ide_rows;
#endif
    Float ide_idx; // per-sample''',1)
a='''    a->ide_idx = {.shape = {B_TT, 4}};''';assert a in s
s=s.replace(a,a+'''
#ifdef PUF_ID_ROWS
    a->ide_rows={.shape={23,B_TT+1}};alloc_register(acts,&a->ide_rows);
#endif''',1)
a='''    nh_idemb_grad_kernel<<<''';assert s.count(a)==1
s=s.replace(a,'''#ifdef PUF_ID_ROWS
    nh_identity_rows<<<1,32,0,stream>>>(a->ide_rows.data,a->ide_idx.data,B);
#endif
'''+a,1)
a='''        a->ide_algn_wgrad.data, grad_concat.data, a->ide_idx.data, B);'''
b='''        a->ide_algn_wgrad.data, grad_concat.data, a->ide_idx.data, B
#ifdef PUF_ID_ROWS
        ,a->ide_rows.data
#endif
        );'''
assert a in s;s=s.replace(a,b,1);p.write_text(s)
