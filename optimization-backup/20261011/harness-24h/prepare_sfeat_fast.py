from pathlib import Path
import re,difflib,json,hashlib
r=Path(__file__).resolve().parent
p=r/'source/ocean/nethack/nethack.cu';old=p.read_text();s=old
assert 'nh_sfeat_fast_mode' not in s
ref=(r/'sfeat_reference.cu.txt').read_text()
# Packed stores keep the existing arithmetic and signed-byte decoding intact.
packed=ref.replace('nh_inv_sfeat_kernel(', 'nh_inv_sfeat_packed_kernel(')
packed=packed.replace('precision_t* f = out + (int64_t)t * NH_SFEAT;', 'alignas(16) precision_t f[NH_SFEAT];')
end=packed.rfind('}')
packed=packed[:end]+'''    static_assert(NH_SFEAT * sizeof(precision_t) % 16 == 0, "packed store alignment");
    uint4* dst = (uint4*)(out + (int64_t)t * NH_SFEAT);
    const uint4* values = (const uint4*)f;
    #pragma unroll
    for (int i = 0; i < NH_SFEAT * sizeof(precision_t) / 16; i++) dst[i] = values[i];
'''+packed[end:]
flat=r'''
__global__ void nh_inv_sfeat_flat_kernel(precision_t* __restrict__ out,
    const nh_obs_t* __restrict__ obs, int B) {
    int t = blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= B * NH_INV * NH_SFEAT) return;
    int d = t % NH_SFEAT, item = t / NH_SFEAT;
    int b = item / NH_INV, slot = item % NH_INV;
    const nh_obs_t* src = obs + (int64_t)b * NH_OBS_SIZE + NH_INVST_OFF + slot * NH_ST_RAW;
    float f;
    if (d < 17) {
        int field = d < 4 ? 0 : d < 6 ? 1 : d == 6 ? 2 : d < 9 ? d - 4 : d < 16 ? 5 : 6;
        int v = (int)nh_obs_float(src[field]);
        int st = v >= 128 ? v - 256 : v;
        if (d < 4) f = st == d ? 1.0f : 0.0f;
        else if (d == 4) f = (float)(st != -128);
        else if (d == 5) f = st != -128 ? fmaxf(fminf((float)st, 7.0f), -7.0f) * (1.0f / 7.0f) : 0.0f;
        else if (d == 6) f = fminf(fmaxf((float)st, 0.0f), 30.0f) * (1.0f / 30.0f);
        else if (d < 9) f = (float)st * (1.0f / 3.0f);
        else if (d < 16) f = (float)((st >> (d - 9)) & 1);
        else f = (float)st;
    } else {
        const nh_obs_t* gsrc = obs + (int64_t)b * NH_OBS_SIZE + NH_INV_OFF + 2 * slot;
        int g = (int)nh_obs_float(gsrc[0]) + ((int)nh_obs_float(gsrc[1]) << 8);
        int ot = g - NH_GLYPH_OBJ_OFF;
        int cat = (ot >= 0 && ot < NH_NUM_OBJECTS) ? nh_obj_armcat_dev[ot] : -1;
        f = cat == d - 17 ? 1.0f : 0.0f;
    }
    out[t] = from_float(f);
}
'''
kernels=packed+'\n'+flat
(r/'sfeat_fast_kernels.cuh.txt').write_text(kernels)
(p.parent/'sfeat_fast.cuh').write_text(kernels)
wrapper='''#include "sfeat_fast.cuh"
static int nh_sfeat_fast_mode = getenv("NH_SFEAT_FAST") ? atoi(getenv("NH_SFEAT_FAST")) : 0;
static void nh_sfeat_launch(precision_t* out, const nh_obs_t* obs, int B, cudaStream_t stream) {
    if (nh_sfeat_fast_mode == 1)
        nh_inv_sfeat_packed_kernel<<<grid_size(B * NH_INV), BLOCK_SIZE, 0, stream>>>(out, obs, B);
    else if (nh_sfeat_fast_mode == 2)
        nh_inv_sfeat_flat_kernel<<<grid_size(B * NH_INV * NH_SFEAT), BLOCK_SIZE, 0, stream>>>(out, obs, B);
    else
        nh_inv_sfeat_kernel<<<grid_size(B * NH_INV), BLOCK_SIZE, 0, stream>>>(out, obs, B);
}

'''
needle='__global__ void nh_inv_gather_kernel('
assert s.count(needle)==1
s=s.replace(needle,wrapper+needle)
pattern=r'    nh_inv_sfeat_kernel<<<[^\n]+>>>\(\n        a->inv_sfeat.data, \(const nh_obs_t\*\)input.data, B\);'
s,n=re.subn(pattern,'    nh_sfeat_launch(a->inv_sfeat.data, (const nh_obs_t*)input.data, B, stream);',s)
assert n==1,n
p.write_text(s)
(r/'SFEAT_FAST.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='before/nethack.cu',tofile='after/nethack.cu')))
(r/'SFEAT_FAST_SOURCE.json').write_text(json.dumps(dict(before=hashlib.sha256(old.encode()).hexdigest(),after=hashlib.sha256(s.encode()).hexdigest(),kernels=hashlib.sha256(kernels.encode()).hexdigest(),flag='NH_SFEAT_FAST 1 packed stores,2 contiguous output threads;default0',status='Prepared; not compiled or validated'),indent=2))
bp=r/'build.py';bs=bp.read_text();assert 'sfeat_fast.cuh' not in bs
bp.write_text(bs.replace("'ocean/nethack/pass_fast.cuh'","'ocean/nethack/pass_fast.cuh','ocean/nethack/sfeat_fast.cuh'"))
print('Prepared packed and contiguous-store scalar-feature variants, default off.')
