from pathlib import Path
import re
r=Path(__file__).parent;p=r/'source/src/pufferl.cu';s=p.read_text();(r/'pufferl.before-byte.cu').write_text(s)
a='''    bufs->observations = {.shape = {T, B, input_size}};'''
b='''#ifdef PUF_BYTE_OBS
    static_assert(sizeof(obs_t)==1 && sizeof(precision_t)==2,"byte observations require BF16 storage containers");
    assert(input_size%2==0);
    // Packed byte pairs: this field is bitwise storage, not BF16 numeric data.
    bufs->observations = {.shape = {T,B,input_size/2}};
#else
'''+a+'\n#endif';assert a in s;s=s.replace(a,b,1)
a='''    // Env obs -> rollout: D2D if same type, else cast (float/uchar → precision_t).
    if (sizeof(obs_t) == sizeof(precision_t)) {'''
b='''#ifdef PUF_BYTE_OBS
    cudaMemcpyAsync(obs_dst.data,obs_env->data+(long)start*obs_env->shape[1],n,cudaMemcpyDeviceToDevice,stream);
#else
'''+a;assert a in s;s=s.replace(a,b,1)
a='''    Prec rew_dst = puf_slice(rollouts.rewards, t, start, block_size);''';assert a in s;s=s.replace(a,'#endif\n\n'+a,1);p.write_text(s)
p=r/'source/ocean/nethack/nethack.cu';s=p.read_text();(r/'nethack.before-byte.cu').write_text(s)
# Only observation readers change type. Learned activations/weights remain BF16.
positions=[]
for m in re.finditer(r'(?:__global__|__device__)[^\n]*\b(?:void|int|float)\s+(\w+)\(',s):
 i=m.start();j=s.find('\n}',i)+2
 if j<2:continue
 fn=s[i:j]
 if 'const precision_t* __restrict__ obs' in fn or m.group(1)=='nh_bl_read_i32':positions.append((i,j,m.group(1)))
print('readers',[n for i,j,n in positions])
for i,j,name in reversed(positions):
 fn=s[i:j]
 names=['obs'] if name!='nh_bl_read_i32' else ['p']
 fn=fn.replace('const precision_t* __restrict__ obs','const nh_obs_t* __restrict__ obs')
 if name=='nh_bl_read_i32':fn=fn.replace('const precision_t* p','const nh_obs_t* p')
 for m in re.finditer(r'const precision_t\* (\w+) = obs',fn):names.append(m.group(1))
 fn=re.sub(r'const precision_t\* (\w+) = obs',r'const nh_obs_t* \1 = obs',fn)
 for n in names:fn=fn.replace('to_float('+n+'[','nh_obs_float('+n+'[')
 s=s[:i]+fn+s[j:]
start=s.index('static Prec nethack_encoder_forward(');end=s.index('\n}',start)+2
fn=s[start:end].replace('input.data','(const nh_obs_t*)input.data');s=s[:start]+fn+s[end:]
header='''#ifdef PUF_BYTE_OBS
using nh_obs_t=unsigned char;
__device__ __forceinline__ float nh_obs_float(nh_obs_t v){return (float)v;}
#else
using nh_obs_t=precision_t;
__device__ __forceinline__ float nh_obs_float(nh_obs_t v){return to_float(v);}
#endif

'''
s=header+s;p.write_text(s)
