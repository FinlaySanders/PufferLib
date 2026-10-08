from pathlib import Path
r=Path(__file__).parent;p=r/'source/ocean/nethack/nethack.cu';s=p.read_text()
code='''#ifdef PUF_ENTITY_WMMA
#if defined(PUF_GROUP_ENTITY) || defined(PUF_FUSE_ENTITY_POOL) || defined(NH_ENT_LINPOOL) || defined(PRECISION_FLOAT)
#error "WMMA prototype requires BF16 standard entity layers"
#endif
#include <mma.h>
__global__ void nh_entity_wmma(const precision_t* x,const precision_t* w1,const precision_t* b1,
        const precision_t* w2,const precision_t* b2,precision_t* hidden,precision_t* out,int M) {
    using namespace nvcuda;
    __shared__ __align__(32) precision_t sx[16*16],sw1[64*16],sw2[64*64],sh[16*64];
    __shared__ __align__(32) float tmp[16*64];
    int tid=threadIdx.x,warp=tid/32,row0=blockIdx.x*16;
    for(int i=tid;i<16*16;i+=128)sx[i]=row0+i/16<M?x[(row0+i/16)*16+i%16]:from_float(0.f);
    for(int i=tid;i<64*16;i+=128)sw1[i]=w1[i];
    for(int i=tid;i<64*64;i+=128)sw2[i]=w2[i];
    __syncthreads();
    wmma::fragment<wmma::matrix_a,16,16,16,precision_t,wmma::row_major> a;
    wmma::fragment<wmma::matrix_b,16,16,16,precision_t,wmma::col_major> b;
    wmma::fragment<wmma::accumulator,16,16,16,float> c;
    wmma::fill_fragment(c,0.f);wmma::load_matrix_sync(a,sx,16);wmma::load_matrix_sync(b,sw1+warp*16*16,16);
    wmma::mma_sync(c,a,b,c);wmma::store_matrix_sync(tmp+warp*16,c,64,wmma::mem_row_major);
    __syncthreads();
    for(int i=tid;i<16*64;i+=128) {
        auto v=from_float(fmaxf(0.f,to_float(from_float(tmp[i]))+to_float(b1[i%64])));sh[i]=v;
        if(row0+i/64<M)hidden[(row0+i/64)*64+i%64]=v;
    }
    __syncthreads();wmma::fill_fragment(c,0.f);
    for(int k=0;k<64;k+=16) {
        wmma::load_matrix_sync(a,sh+k,64);wmma::load_matrix_sync(b,sw2+warp*16*64+k,64);
        wmma::mma_sync(c,a,b,c);
    }
    wmma::store_matrix_sync(tmp+warp*16,c,64,wmma::mem_row_major);__syncthreads();
    for(int i=tid;i<16*64;i+=128)if(row0+i/64<M)
        out[(row0+i/64)*64+i%64]=from_float(fmaxf(0.f,to_float(from_float(tmp[i]))+to_float(b2[i%64])));
}
#endif

'''
a='static Prec nethack_encoder_forward(';assert a in s;s=s.replace(a,code+a,1)
for x,w1,b1,h1,w2,b2,v,slots,line in [
 ('inv_out','mv1_w','mv1_b','mh1','mv2_w','mv2_b','mvv','NH_INV','NH_MM_BR(&invf, &ew->mv1_w, &h1f, ew->mv1_b);'),
 ('mrp','mm1_w','mm1_b','mh1m','mm2_w','mm2_b','mvm','NH_LABK','NH_MM_BR(&rpf, &ew->mm1_w, &h1f, ew->mm1_b);'),
 ('irp','im1_w','im1_b','mh1i','im2_w','im2_b','mvi','NH_LABK','NH_MM_BR(&rpf, &ew->im1_w, &h1f, ew->im1_b);'),
 ('spk_keys','spm1_w','spm1_b','sph1','spm2_w','spm2_b','spv','NH_SPELL_SLOTS','NH_MM_BR(&kf, &ew->spm1_w, &hf, ew->spm1_b);')]:
 assert line in s
 prefix=f'''\n#ifdef PUF_ENTITY_WMMA
      if(B<=128)nh_entity_wmma<<<(B*{slots}+15)/16,128,0,stream>>>(a->{x}.data,ew->{w1}.data,ew->{b1}.data,ew->{w2}.data,ew->{b2}.data,a->{h1}.data,a->{v}.data,B*{slots});
      else
#endif
      '''
 s=s.replace(line,prefix+line,1)
 import re
 pat=r'NH_ENT_LAST\([^\n]*&ew->'+w2+r'[^\n]*;'
 m=re.search(pat,s);assert m,w2
 s=s[:m.start()]+'\n#ifdef PUF_ENTITY_WMMA\n      if(B>128)\n#endif\n      '+s[m.start():]
p.write_text(s)
