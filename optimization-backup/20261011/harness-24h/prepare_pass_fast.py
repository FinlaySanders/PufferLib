from pathlib import Path
import difflib
import hashlib
import json
import re

r=Path(__file__).resolve().parent
p=r/'source/ocean/nethack/nethack.cu'
old=p.read_text();s=old
assert 'nh_pass_fast_mode' not in s
for name in ['nh_pass_kernel','nh_passbwd_kernel']:
    pattern=r'    '+name+r'<<<[^\n]+>>>\(([\s\S]*?)\);'
    def replacement(m):
        args=m.group(1)
        assert args.endswith('B')
        return '    '+name.removesuffix('_kernel')+'_launch('+args+', stream);'
    s,n=re.subn(pattern,replacement,s)
    assert n==2,(name,n)
needle='__global__ void nh_patch_max_bwd_kernel('
wrappers='''#include "pass_fast.cuh"
static int nh_pass_fast_mode = getenv("NH_PASS_FAST") ? atoi(getenv("NH_PASS_FAST")) : 0;
static void nh_pass_launch(precision_t* dst, const precision_t* values,
        const precision_t* features, const float* ids, int disabled, int offset,
        int B, cudaStream_t stream) {
    if (nh_pass_fast_mode & 1)
        nh_pass_fast_kernel<<<B, 256, 0, stream>>>(dst, values, features, ids, disabled, offset, B);
    else
        nh_pass_kernel<<<grid_size(B * NH_PASS_DIM), BLOCK_SIZE, 0, stream>>>(dst, values, features, ids, disabled, offset, B);
}
static void nh_passbwd_launch(precision_t* dst, const precision_t* gradient,
        const precision_t* features, const float* ids, int disabled, int offset,
        int B, cudaStream_t stream) {
    if (nh_pass_fast_mode & 2)
        nh_passbwd_fast_kernel<<<B, 256, 0, stream>>>(dst, gradient, features, ids, disabled, offset, B);
    else
        nh_passbwd_kernel<<<grid_size((int64_t)B * NH_INV * NH_INV_HID), BLOCK_SIZE, 0, stream>>>(dst, gradient, features, ids, disabled, offset, B);
}

'''
assert s.count(needle)==1
s=s.replace(needle,wrappers+needle)
(r/'PASS_FAST.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/nethack.cu',tofile='after/nethack.cu')))
p.write_text(s)
(p.parent/'pass_fast.cuh').write_text((r/'pass_fast_kernels.cuh.txt').read_text())
(r/'PASS_FAST_SOURCE.json').write_text(json.dumps(dict(before=hashlib.sha256(old.encode()).hexdigest(),after=hashlib.sha256(s.encode()).hexdigest(),kernel=hashlib.sha256((p.parent/'pass_fast.cuh').read_bytes()).hexdigest(),flag='NH_PASS_FAST bits1forward/2backward',status='Prepared; not compiled or validated'),indent=2))
print('Prepared one-per-sample equipment selection metadata. Default path unchanged.')
