from pathlib import Path
import json,shutil,difflib,hashlib
r=Path(__file__).resolve().parent
base=Path('/puffertank/experiments/nethack-compact-state-20261008/engines/movement_object_presence_pgo_followthrough/source')
d=r/'floor_boxes';d.mkdir(exist_ok=False)
for name in ['control','candidate']:
 shutil.copytree(base,d/name/'source',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
src=d/'candidate/source'
p=src/'include/nh_ctx_gen.h';s=p.read_text()
needle='    int g_nh_fobj_count; /* global: nh_fobj_count */'
assert s.count(needle)==1
s=s.replace(needle,needle+'''\n    short g_nh_fobj_box_lx[64], g_nh_fobj_box_hx[64];
    short g_nh_fobj_box_ly[64], g_nh_fobj_box_hy[64];''')
needle='#define nh_fobj_count (nh_cur->g_nh_fobj_count)'
assert s.count(needle)==1
s=s.replace(needle,needle+'''\n#define nh_fobj_box_lx (nh_cur->g_nh_fobj_box_lx)
#define nh_fobj_box_hx (nh_cur->g_nh_fobj_box_hx)
#define nh_fobj_box_ly (nh_cur->g_nh_fobj_box_ly)
#define nh_fobj_box_hy (nh_cur->g_nh_fobj_box_hy)''');p.write_text(s)
p=src/'src/monmove.c';s=p.read_text()
needle='        nh_fobj_x[n] = o->ox; nh_fobj_y[n] = o->oy;'
assert s.count(needle)==1
s=s.replace(needle,needle+'''
        if ((n & 31) == 0) {
            nh_fobj_box_lx[n / 32] = nh_fobj_box_hx[n / 32] = o->ox;
            nh_fobj_box_ly[n / 32] = nh_fobj_box_hy[n / 32] = o->oy;
        } else {
            int box = n / 32;
            if (o->ox < nh_fobj_box_lx[box]) nh_fobj_box_lx[box] = o->ox;
            if (o->ox > nh_fobj_box_hx[box]) nh_fobj_box_hx[box] = o->ox;
            if (o->oy < nh_fobj_box_ly[box]) nh_fobj_box_ly[box] = o->oy;
            if (o->oy > nh_fobj_box_hy[box]) nh_fobj_box_hy[box] = o->oy;
        }''')
needle='''        while (cursor->index + 8 <= nh_fobj_count) {
            int i = cursor->index;'''
assert s.count(needle)==1
s=s.replace(needle,'''        int box_end = 0;
        while (cursor->index + 8 <= nh_fobj_count) {
            int i = cursor->index;
            if (i >= box_end) {
                int box = i / 32;
                box_end = (box + 1) * 32;
                if (nh_fobj_box_hx[box] < lx || nh_fobj_box_lx[box] > hx
                    || nh_fobj_box_hy[box] < ly || nh_fobj_box_ly[box] > hy) {
                    cursor->index = min(box_end, nh_fobj_count);
                    continue;
                }
            }''')
p.write_text(s)
patch=[];files=['include/nh_ctx_gen.h','src/monmove.c']
for f in files:
 patch+=difflib.unified_diff((base/f).read_text().splitlines(True),(src/f).read_text().splitlines(True),fromfile='control/'+f,tofile='candidate/'+f)
(d/'changes.patch').write_text(''.join(patch))
(d/'SOURCE.json').write_text(json.dumps({f:dict(control=hashlib.sha256((base/f).read_bytes()).hexdigest(),candidate=hashlib.sha256((src/f).read_bytes()).hexdigest()) for f in files},indent=2))
print('Prepared two ordinary-LTO engine sources and conservative32-item bounding boxes; no build.')
