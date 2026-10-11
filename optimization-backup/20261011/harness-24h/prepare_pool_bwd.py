from pathlib import Path
import json,difflib,re
r=Path('.')
p=r/'source/ocean/nethack/nethack.cu';old=p.read_text();s=old
anchor='static void nh_relu_bias_backward('
assert s.count(anchor)==1
wrapper='''#include "pool_bwd.cuh"

template<int N, int PAD, int OFF, int DIM>
static void nh_entity_pool_backward(precision_t* dv, const precision_t* gc,
        const float* am, const float* gid, const precision_t* out,
        long long* bias, float eps, int B, cudaStream_t stream) {
    static int mode = getenv("NH_POOL_BWD") ? atoi(getenv("NH_POOL_BWD")) : 0;
    assert(mode >= 0 && mode <= 2);
    int64_t total = (int64_t)B * N * DIM;
    int bias_grid = nh_colsum_grid(total, DIM);
#ifndef NH_ENT_LINPOOL
    if (NH_MV == 64 && DIM == 64 && mode == 2) {
        pool_dv_relu_bias<N,PAD,OFF><<<bias_grid, BLOCK_SIZE, DIM * sizeof(long long), stream>>>(
            dv, gc, am, gid, eps, B, out, bias);
        return;
    }
    if (NH_MV == 64 && DIM == 64 && mode == 1) {
        pool_dv_specialized<N,PAD,OFF><<<grid_size(total), BLOCK_SIZE, 0, stream>>>(
            dv, gc, am, gid, eps, B);
    } else
#endif
    {
        nh_min_dv_kernel<<<grid_size(total), BLOCK_SIZE, 0, stream>>>(
            dv, gc, am, gid, eps, N, PAD, OFF, B);
    }
    NH_ENT_LAST_BWD<<<bias_grid, BLOCK_SIZE, DIM * sizeof(long long), stream>>>(
        dv, out, bias, total, DIM);
}

'''
s=s.replace(anchor,wrapper+anchor,1)
for dv,amax,gid,v,bias,n,pad,off,dim,eps in [
 ('mdv','mvmax','inv_idx','mvv','mv2b_acc','NH_INV','NH_PAD_GLYPH','NH_MINV_OFF','NH_MV','0.2f'),
 ('spdv','spvmax','spell_idx','spv','spm2b_acc','NH_SPELL_SLOTS','-1','NH_SPELL_CONCAT_OFF','NH_SPM','0.25f'),
 ('mdvm','mvmaxm','lm_gid','mvm','mm2b_acc','NH_LABK','-1','NH_MLM_OFF','NH_MV','0.25f'),
 ('mdvi','mvmaxi','li_gid','mvi','im2b_acc','NH_LABK','-1','NH_MLI_OFF','NH_MV','0.25f')]:
 needle='        a->'+dv+'.data, grad_concat.data, a->'+amax+'.data, a->'+gid+'.data,'
 pos=s.index(needle,s.index('static void nethack_encoder_backward'))
 start=s.rfind('    nh_min_dv_kernel<<<',0,pos)
 end=s.index('    nh_fxp_to_precision_kernel<<<',pos)
 block=s[start:end]
 assert 'NH_ENT_LAST_BWD' in block
 memsets=''.join(re.findall(r'    cudaMemsetAsync\([^\n]+\n',block))
 replacement=memsets+f'''    nh_entity_pool_backward<{n}, {pad}, {off}, {dim}>(
        a->{dv}.data, grad_concat.data, a->{amax}.data, a->{gid}.data,
        a->{v}.data, (long long*)a->{bias}.data, {eps}, B, stream);
'''
 s=s[:start]+replacement+s[end:]
p.write_text(s)
(r/'POOL_BWD.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='ocean/nethack/nethack.cu',tofile='ocean/nethack/nethack.cu')))
(r/'source/ocean/nethack/pool_bwd.cuh').write_bytes((r/'pool_bwd_candidate.cuh').read_bytes())
p=r/'build.py';s=p.read_text().replace("'ocean/nethack/nethack.cu'","'ocean/nethack/nethack.cu','ocean/nethack/pool_bwd.cuh'");p.write_text(s)
env=json.loads((r/'PRIORITY_CANDIDATE.json').read_text())['environment'];env.pop('PUF_ROLLOUT_DETAIL',None)
for kind,title,args,cases in [('time','GPU',['--trials=5'],[('base_a',0),('specialized',1),('fused',2),('base_b',0)]),('full','FULL',['--epochs=80','--start=64'],[('base_a',0),('fused',2),('base_b',0)])]:
 jobs=[dict(label='pool_bwd_'+kind+'_'+tag,kind=kind,binary='pool_bwd_v35',env=dict(env,NH_POOL_BWD=mode),args=args) for tag,mode in cases]
 (r/('POOL_BWD_'+title+'.json')).write_text(json.dumps(jobs,indent=2))
