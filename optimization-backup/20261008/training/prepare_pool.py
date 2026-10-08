from pathlib import Path
r=Path(__file__).parent;p=r/'source/ocean/nethack/nethack.cu';s=p.read_text();a=s.index('__global__ void nh_min_summax_kernel(');b=s.index('// dv = broadcast',a);t=s[a:b]
t=t.replace('nh_min_summax_kernel','nh_min_summax_bias_kernel').replace('const precision_t* __restrict__ v,','precision_t* __restrict__ v,').replace('int off, int B) {','int off, int B, const precision_t* __restrict__ bias) {')
old='''        if (bad) continue;
        float vv = to_float(v[((int64_t)b * n + k) * NH_MV + d]);'''
new='''        long vi=((int64_t)b*n+k)*NH_MV+d;
        precision_t activated=from_float(fmaxf(0.0f,to_float(v[vi])+to_float(bias[d])));
        v[vi]=activated;
        if(bad)continue;
        float vv=to_float(activated);'''
assert old in t;t=t.replace(old,new)
s=s[:b]+'''#ifdef PUF_FUSE_ENTITY_POOL
#ifdef NH_ENT_LINPOOL
#error "Fused pool only implemented for ReLU entity outputs"
#endif
'''+t+'''#define NH_SUMMAX nh_min_summax_bias_kernel
#define NH_POOL_BIAS(p) ,p
#else
#define NH_SUMMAX nh_min_summax_kernel
#define NH_POOL_BIAS(p)
#endif

'''+s[b:]
a='static inline int nh_colsum_grid';i=s.index(a)
s=s[:i]+'''#ifdef PUF_FUSE_ENTITY_POOL
#undef NH_ENT_LAST
#define NH_ENT_LAST(A,W,O,BIAS) puf_mm((A),(W),(O),stream)
#endif
'''+s[i:]
s=s.replace('    nh_min_summax_kernel<<<','    NH_SUMMAX<<<')
for tail,bias in [('NH_MINV_OFF','mv2_b'),('NH_MLM_OFF','mm2_b'),('NH_MLI_OFF','im2_b'),('NH_SPELL_CONCAT_OFF','spm2_b')]:
 old=tail+', B);';new=tail+', B NH_POOL_BIAS(ew->'+bias+'.data));';assert old in s;s=s.replace(old,new,1)
p.write_text(s)
