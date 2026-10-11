from pathlib import Path
import json, difflib

r = Path('.')
p = r/'source/src/algo.cu'
old = p.read_text()
s = old.replace('#include "entity_fused.cuh"', '#include "entity_fused.cuh"\n#include "entity_train_fused.cuh"', 1)
s = s.replace('    entity_fused_init();', '    entity_fused_init();\n    entity_train_fused_init();', 1)
assert s != old
p.write_text(s)
patch = ''.join(difflib.unified_diff(old.splitlines(True), s.splitlines(True), fromfile='src/algo.cu', tofile='src/algo.cu'))
p = r/'source/ocean/nethack/nethack.cu'
old = p.read_text()
s = old
for name, idx, inp, w1, w2, gid, amax, h1, v, dims in [
    ('inventory', 0, 'inv_out', 'mv1', 'mv2', 'inv_idx', 'mvmax', 'mh1', 'mvv', 'NH_MINV_OFF == 1010 && NH_INV == 55'),
    ('monster', 1, 'mrp', 'mm1', 'mm2', 'lm_gid', 'mvmaxm', 'mh1m', 'mvm', 'NH_MLM_OFF == 1394 && NH_LABK == 16'),
    ('item', 2, 'irp', 'im1', 'im2', 'li_gid', 'mvmaxi', 'mh1i', 'mvi', 'NH_MLI_OFF == 1538 && NH_LABK == 16'),
    ('spell', 3, 'spk_keys', 'spm1', 'spm2', 'spell_idx', 'spvmax', 'sph1', 'spv', 'NH_SPELL_CONCAT_OFF == 838 && NH_SPELL_SLOTS == 8 && NH_SPM == 64 && NH_SPKEY == 16'),
]:
    end = s.index('#endif', s.index('    bool '+name+'_fused = false;'))
    insert = f'''    if (a->training && !nh_fused_br_active && NH_CONCAT == 1698
            && NH_INV_HID == 16 && NH_MV == 64 && {dims})
        {name}_fused = entity_train_fused_try({idx}, a->{inp}.data,
            ew->{w1}_w.data, ew->{w1}_b.data, ew->{w2}_w.data, ew->{w2}_b.data,
            a->{gid}.data, a->concat.data, a->{amax}.data,
            a->{h1}.data, a->{v}.data, B, stream);
'''
    s = s[:end] + insert + s[end:]
p.write_text(s)
patch += ''.join(difflib.unified_diff(old.splitlines(True), s.splitlines(True), fromfile='ocean/nethack/nethack.cu', tofile='ocean/nethack/nethack.cu'))
(r/'ENTITY_TRAIN_FUSED.patch').write_text(patch)
(r/'source/src/entity_train_fused.cuh').write_bytes((r/'entity_train_fused.cuh.generated').read_bytes())
p = r/'build.py'
s = p.read_text().replace("'src/entity_fused.cuh'", "'src/entity_fused.cuh','src/entity_train_fused.cuh'")
p.write_text(s)
env = json.loads((r/'PRIORITY_CANDIDATE.json').read_text())['environment']
env.pop('PUF_ROLLOUT_DETAIL', None)
for kind, title, args, cases in [
    ('time', 'GPU', ['--trials=5'], [('base_a',0,0),('inventory',1,0),('other',14,0),('all',15,0),('base_b',0,0)]),
    ('full', 'FULL', ['--epochs=80','--start=64'], [('base_a',0,0),('train',15,0),('both',15,15),('base_b',0,0)])
]:
    jobs = [dict(label='entity_train_'+kind+'_'+tag, kind=kind, binary='entity_train_v34', env=dict(env, NH_ENTITY_TRAIN_FUSED=train, NH_ENTITY_FUSED=infer), args=args) for tag, train, infer in cases]
    (r/('ENTITY_TRAIN_'+title+'.json')).write_text(json.dumps(jobs, indent=2))
