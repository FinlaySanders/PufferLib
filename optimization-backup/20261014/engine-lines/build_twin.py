"""Debug-symbol twin of a PGO engine for perf line attribution: same source, same profiles (copied with the build path renamed),
-g added, coverage mismatch downgraded to a warning (generated util parsers only). usage: build_twin.py <name>  -> engines/<name>_g/build"""
from pathlib import Path
import shutil, subprocess, sys, re
R=Path(__file__).resolve().parent; name=sys.argv[1]; E=R/'engines'/name; G=R/'engines'/(name+'_g')
assert (E/'profiles').exists() and (E/'build/libnethack.so').exists()
if G.exists(): shutil.rmtree(G)
(G/'profiles').mkdir(parents=True)
old=f'#engines#{name}#build#'; new=f'#engines#{name}_g#build#'
for f in (E/'profiles').glob('*.gcda'): shutil.copy2(f, G/'profiles'/f.name.replace(old,new))
F=f'-fno-semantic-interposition -fprofile-use={G}/profiles -fprofile-correction -Wno-error=coverage-mismatch -g'
cmd=['cmake','-S',str(E/'source'),'-B',str(G/'build'),'-DCMAKE_BUILD_TYPE=Release','-DNLE_TLS_INITIAL_EXEC=ON','-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON','-DCMAKE_C_FLAGS='+F,'-DCMAKE_CXX_FLAGS='+F]
for dep in ('bzip2','deboost_context','pybind11'): cmd+=['-DFETCHCONTENT_SOURCE_DIR_'+dep.upper()+'=/puffertank/pufferlib/vendor/fast-nle/build/_deps/'+dep+'-src']
with (G/'build.log').open('w') as log:
    subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['cmake','--build',str(G/'build'),'--target','nethack','-j8'],stdout=log,stderr=subprocess.STDOUT,check=True)
def norm(so):
    out=subprocess.run(['objdump','-d','--no-show-raw-insn',so],capture_output=True,text=True).stdout
    return [re.sub(r'<[^>]*>','<>',re.sub(r'0x[0-9a-f]+','HEX',re.sub(r'^\s*[0-9a-f]+:','',l))) for l in out.splitlines()[3:] if not re.match(r'^[0-9a-f]+ <',l)]
a,b=norm(str(E/'build/libnethack.so')),norm(str(G/'build/libnethack.so'))
print('TWIN', name, 'insns', len(a), len(b), 'identical modulo addresses/labels:', a==b)
