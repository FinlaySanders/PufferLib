from pathlib import Path
import json,difflib
r=Path('.')
p=r/'source/src/algo.cu';old=p.read_text();s=old.replace('#include "inventory_fused.cuh"','#include "inventory_fused.cuh"\n#include "entity_fused.cuh"',1).replace('    inventory_fused_init();','    inventory_fused_init();\n    entity_fused_init();',1);p.write_text(s)
patch=''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='src/algo.cu',tofile='src/algo.cu'))
p=r/'source/ocean/nethack/nethack.cu';old=p.read_text();s=old
before='''        inventory_fused = inventory_fused_try(a->inv_out.data,
            ew->mv1_w.data, ew->mv1_b.data, ew->mv2_w.data, ew->mv2_b.data,
            a->inv_idx.data, a->concat.data, a->mvmax.data, a->mh1.data, a->mvv.data, B, stream);'''
after='''        inventory_fused = entity_fused_try(0, a->inv_out.data,
            ew->mv1_w.data, ew->mv1_b.data, ew->mv2_w.data, ew->mv2_b.data,
            a->inv_idx.data, a->concat.data, a->mvmax.data, B, stream)
            || inventory_fused_try(a->inv_out.data,
            ew->mv1_w.data, ew->mv1_b.data, ew->mv2_w.data, ew->mv2_b.data,
            a->inv_idx.data, a->concat.data, a->mvmax.data, a->mh1.data, a->mvv.data, B, stream);'''
assert s.count(before)==1;s=s.replace(before,after)
for name,index,inp,w1,w2,gid,amax,off,ncond,startstr,endstr in [
 ('monster',1,'mrp','mm1','mm2','lm_gid','mvmaxm','NH_MLM_OFF == 1394','NH_LABK == 16','    { Prec rpf = {.data = a->mrp.data','    nh_min_sgate_kernel<<<'),
 ('item',2,'irp','im1','im2','li_gid','mvmaxi','NH_MLI_OFF == 1538','NH_LABK == 16','    { Prec rpf = {.data = a->irp.data','    nh_min_sgate_kernel<<<'),
 ('spell',3,'spk_keys','spm1','spm2','spell_idx','spvmax','NH_SPELL_CONCAT_OFF == 838','NH_SPELL_SLOTS == 8 && NH_SPM == 64','    { Prec kf = {.data = a->spk_keys.data','    nh_sp_doorstep_kernel<<<')]:
 start=s.index(startstr,s.index('static Prec nethack_encoder_forward'))
 end=s.index(endstr,start);block=s[start:end]
 prefix=f'''    bool {name}_fused = false;
#ifndef NH_ENT_LINPOOL
    if (!a->training && NH_CONCAT == 1698 && {off}
            && {ncond} && NH_INV_HID == 16 && NH_MV == 64)
        {name}_fused = entity_fused_try({index}, a->{inp}.data,
            ew->{w1}_w.data, ew->{w1}_b.data, ew->{w2}_w.data, ew->{w2}_b.data,
            a->{gid}.data, a->concat.data, a->{amax}.data, B, stream);
#endif
    if (!{name}_fused) {{
'''
 s=s[:start]+prefix+block+'    }\n'+s[end:]
p.write_text(s);patch+=''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='ocean/nethack/nethack.cu',tofile='ocean/nethack/nethack.cu'))
(r/'ENTITY_FUSED.patch').write_text(patch)
(r/'source/src/entity_fused.cuh').write_bytes((r/'entity_fused.cuh.generated').read_bytes())
p=r/'build.py';s=p.read_text().replace("'src/inventory_fused.cuh'","'src/inventory_fused.cuh','src/entity_fused.cuh'");p.write_text(s)
env=json.loads((r/'PRIORITY_CANDIDATE.json').read_text())['environment'];env.pop('PUF_ROLLOUT_DETAIL',None)
for kind,title,args,cases in [('inference','INFERENCE',['--trials=5'],[('base_a',0),('inventory',1),('other',14),('all',15),('base_b',0)]),('full','FULL',['--epochs=80','--start=64'],[('base_a',0),('all',15),('base_b',0)])]:
 jobs=[dict(label='entity_fused_'+kind+'_'+tag,kind=kind,binary='entity_fused_v33',env=dict(env,NH_ENTITY_FUSED=mask),args=args) for tag,mask in cases]
 (r/('ENTITY_FUSED_'+title+'.json')).write_text(json.dumps(jobs,indent=2))
