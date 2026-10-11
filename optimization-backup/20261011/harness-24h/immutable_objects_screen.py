from pathlib import Path
import hashlib
import json
import shlex
import shutil
import statistics
import subprocess

r = Path(__file__).resolve().parent
d = r / 'immutable_objects'
base = Path(json.loads((r/'IMMUTABLE_OBJECT_READS.json').read_text())['source'])
control = r/'floor_boxes/control'
assert not subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'], text=True).strip()
d.mkdir(exist_ok=False)

# Reuse the unchanged ordinary-LTO control, after checking its source bytes.
for name in ['src', 'include', 'win', 'sys', 'util']:
    for p in (base/name).rglob('*'):
        if p.is_file():
            q = control/'source'/p.relative_to(base)
            assert q.is_file() and p.read_bytes() == q.read_bytes(), str(p)
s = d/'candidate/source'
b = d/'candidate/build'
shutil.copytree(base, s, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
subprocess.run(['patch', '-p1', '--batch', '--input', str(r/'IMMUTABLE_OBJECT_READS.patch')], cwd=s, check=True, stdout=subprocess.DEVNULL)
spec = json.loads((r/'IMMUTABLE_OBJECT_READS.json').read_text())
source_hashes = {}
for name, record in spec['files'].items():
    original = hashlib.sha256((base/name).read_bytes()).hexdigest()
    assert original == record['sha256'], name
    source_hashes[name] = dict(control=original, candidate=hashlib.sha256((s/name).read_bytes()).hexdigest())
(d/'source_hashes.json').write_text(json.dumps(source_hashes,indent=2))
fields = spec['fields']
smoke_source = (r/'immutable_objects_smoke.c.in').read_text().replace('/* GENERATED_CHECKS */', '\n        '.join('CHECK('+f+');' for f in fields))
(d/'smoke.c').write_text(smoke_source)
cmd = ['cmake', '-S', str(s), '-B', str(b), '-DCMAKE_BUILD_TYPE=Release', '-DNLE_TLS_INITIAL_EXEC=ON', '-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON', '-DCMAKE_C_FLAGS=-fno-semantic-interposition', '-DCMAKE_CXX_FLAGS=-fno-semantic-interposition']
for dep in ['bzip2','deboost_context','pybind11']:
    cmd += ['-DFETCHCONTENT_SOURCE_DIR_'+dep.upper()+'=/puffertank/pufferlib/vendor/fast-nle/build/_deps/'+dep+'-src']
(d/'build_command.json').write_text(json.dumps(cmd, indent=2))
print('BUILD immutable item reads, ordinary GCC/LTO matched to existing control', flush=True)
with (d/'build.log').open('w') as f:
    subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
    subprocess.run(['cmake', '--build', str(b), '--target', 'nethack', '-j8'], stdout=f, stderr=subprocess.STDOUT, check=True)
paths = {'control': control/'build', 'candidate': b}
proofs = []
for name, build in paths.items():
    flags = []
    for line in (build/'CMakeFiles/nethack.dir/flags.make').read_text().splitlines():
        for prefix in ['C_DEFINES = ', 'C_INCLUDES = ']:
            if line.startswith(prefix):
                flags += shlex.split(line[len(prefix):])
    binary = d/(name+'_smoke')
    cmd = ['cc','-O2','-g',*flags,str(d/'smoke.c'),'-L'+str(build),'-Wl,-rpath,'+str(build),'-lnethack','-o',str(binary)]
    subprocess.run(cmd, check=True)
    proof = subprocess.check_output([str(binary)], text=True, timeout=30)
    (d/(name+'_smoke.log')).write_text(proof)
    proofs.append(proof)
    print(name, proof.strip(), flush=True)
assert proofs[0] == proofs[1]
rows = []
endpoint = None
for index, name in enumerate(['control', 'candidate', 'candidate', 'control']):
    label = 'immutable_'+name+'_'+str(index)
    print('SCREEN', label, flush=True)
    with (d/(label+'.log')).open('w') as f:
        subprocess.run(['python',str(r/'native_pool/snapshot_test.py'),label,'2048','0:512,0:512','--engine',str(paths[name])], stdout=f, stderr=subprocess.STDOUT, check=True)
    result = json.loads((r/'native_pool/runs'/label/'result.json').read_text())
    cases = [x['result'] for x in result['cases']]
    for case in cases:
        found = tuple(case[k] for k in ['obs', 'turns', 'age'])
        if endpoint is None:
            endpoint = found
        assert found == endpoint, (label, found, endpoint)
    row = dict(label=label, engine=name, sps=statistics.mean(float(x['sps']) for x in cases), cases=cases)
    rows.append(row)
    (d/'results.json').write_text(json.dumps(rows,indent=2))
    print('DONE', label, row['sps'], flush=True)
    if len(rows)==2 and rows[1]['sps'] < rows[0]['sps']*1.008:
        print('PARK below initial 0.8% gate',flush=True)
        break
(d/'binary_hashes.json').write_text(json.dumps({name:hashlib.sha256((p/'libnethack.so').read_bytes()).hexdigest() for name,p in paths.items()},indent=2))
print('IMMUTABLE OBJECT SCREEN COMPLETE',flush=True)
