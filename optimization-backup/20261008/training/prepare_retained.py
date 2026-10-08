from pathlib import Path
import shutil,subprocess,difflib
r=Path(__file__).parent;s=r/'source';d=r/'retained';b=Path('/puffertank/experiments/nethack-batch-sweep-20260918/source')
d.mkdir(exist_ok=True)
for name in ['src','config']:
 shutil.copytree(s/name,d/name,dirs_exist_ok=True)
(d/'ocean').mkdir(exist_ok=True)
for p in (s/'ocean').iterdir():
 q=d/'ocean'/p.name
 if p.name=='nethack':shutil.copytree(p,q,dirs_exist_ok=True)
 elif not q.exists():q.symlink_to(p.resolve(),target_is_directory=p.is_dir())
for name in ['vendor','resources','raylib']:
 if not (d/name).is_symlink() and not (d/name).exists():(d/name).symlink_to((s/name).resolve(),target_is_directory=True)
shutil.copy2(s/'build.sh',d/'build.sh')
reject='PUF_BIAS_REDUCE PUF_LT_CHOICE PUF_SM_TARGET PUF_DW_DEFER PUF_DW_SERIAL PUF_STREAM_PRIORITY PUF_SCAN_PACK PUF_COMPACT_NORM PUF_MUON_FUSE_CAST PUF_MUON_FINISH PUF_MUON_PARALLEL PUF_CACHE_TABLES PUF_BATCH_UPLOAD PUF_SAMPLE_TIMING PUF_FUSE_ENTITY_POOL PUF_MSG_PAIR PUF_DIRECT_BIAS PUF_ID_ROWS PUF_GROUP_ENTITY PUF_ENTITY_WMMA'.split()
paths=['src/algo.cu','src/pufferl.cu','ocean/nethack/nethack.cu']
for rel in paths:
 p=d/rel
 out=subprocess.run([str(r/'tools/usr/bin/unifdef'),*[f'-U{x}' for x in reject],str(p)],capture_output=True,text=True)
 assert out.returncode in (0,1),out.stderr
 p.write_text(out.stdout)
p=d/'src/algo.cu';t=p.read_text();orig=(r/'algo.baseline.cu').read_text()
# Restore unchanged scan kernels and launch geometry after rejecting scan experiments.
for name in ('forward','backward'):
 marker='__global__ void mingru_scan_'+name+'_row('
 i=t.index(marker);j=t.index('\n}\n',i)+3
 oi=orig.index(marker);oj=orig.index('\n}\n',oi)+3
 t=t[:i]+orig[oi:oj]+t[j:]
t=t.replace('#ifndef PUF_MINGRU_LOAD_ROWS\n#define PUF_MINGRU_LOAD_ROWS 32\n#endif\n','').replace('dim3 block(MINGRU_TILE, PUF_MINGRU_LOAD_ROWS);','dim3 block(MINGRU_TILE, MINGRU_TILE);')
t=t.replace('cudaStream_t stream = 0, precision_t* low = nullptr)', 'cudaStream_t stream = 0)')
t=t.replace('Prec dst = (i % 2 == 0) ? x_buf : x;', 'Prec& dst = (i % 2 == 0) ? x_buf : x;')
p.write_text(t)
shutil.copy2(b/'src/nethack_sampler.cuh',d/'src/nethack_sampler.cuh')
patch=[]
for rel in paths:
 old=(b/rel).read_text().splitlines(keepends=True);new=(d/rel).read_text().splitlines(keepends=True)
 patch.extend(difflib.unified_diff(old,new,fromfile='a/'+rel,tofile='b/'+rel))
(r/'retained.patch').write_text(''.join(patch))
print('retained patch lines',len(patch))
# Reapply just the byte reader conversion to the original encoder.
import re
p=d/'ocean/nethack/nethack.cu';t=(r/'nethack.baseline.cu').read_text();positions=[]
for m in re.finditer(r'(?:__global__|__device__)[^\n]*\b(?:void|int|float)\s+(\w+)\(',t):
 i=m.start();j=t.find('\n}',i)+2
 if j>1 and ('const precision_t* __restrict__ obs' in t[i:j] or m.group(1)=='nh_bl_read_i32'):positions.append((i,j,m.group(1)))
for i,j,name in reversed(positions):
 fn=t[i:j];names=['p'] if name=='nh_bl_read_i32' else ['obs']
 fn=fn.replace('const precision_t* __restrict__ obs','const nh_obs_t* __restrict__ obs')
 if name=='nh_bl_read_i32':fn=fn.replace('const precision_t* p','const nh_obs_t* p')
 changed=True
 while changed:
  changed=False
  for m in re.finditer(r'const precision_t\* (\w+) = (\w+)\b',fn):
   if m.group(2) in names:
    names.append(m.group(1));fn=fn.replace(m.group(0),m.group(0).replace('precision_t','nh_obs_t'));changed=True;break
 for n in names:fn=fn.replace('to_float('+n+'[','nh_obs_float('+n+'[')
 t=t[:i]+fn+t[j:]
i=t.index('static Prec nethack_encoder_forward(');j=t.index('\n}',i)+2
t=t[:i]+t[i:j].replace('input.data','(const nh_obs_t*)input.data')+t[j:]
header=(s/'ocean/nethack/nethack.cu').read_text().split('\n\n',1)[0]+'\n\n'
p.write_text(header+t)
p=d/'src/pufferl.cu';t=p.read_text().replace('    int original_t=t;\n','');p.write_text(t)
patch=[]
for rel in paths:patch.extend(difflib.unified_diff((b/rel).read_text().splitlines(keepends=True),(d/rel).read_text().splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
(r/'retained.patch').write_text(''.join(patch))
print('cleaned patch lines',len(patch))
