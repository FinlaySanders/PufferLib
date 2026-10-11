from pathlib import Path
import json,subprocess,shlex,time,hashlib
r=Path(__file__).resolve().parent;d=r/'floor_boxes'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
subprocess.run(['python',str(r/'prepare_floor_boxes.py')],cwd=r,check=True)
for name in ['control','candidate']:
 s=d/name/'source';b=d/name/'build'
 cmd=['cmake','-S',str(s),'-B',str(b),'-DCMAKE_BUILD_TYPE=Release','-DNLE_TLS_INITIAL_EXEC=ON','-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON','-DCMAKE_C_FLAGS=-fno-semantic-interposition','-DCMAKE_CXX_FLAGS=-fno-semantic-interposition']
 for dep in ['bzip2','deboost_context','pybind11']:cmd+=['-DFETCHCONTENT_SOURCE_DIR_'+dep.upper()+'=/puffertank/pufferlib/vendor/fast-nle/build/_deps/'+dep+'-src']
 (d/name/'command.json').write_text(json.dumps(cmd,indent=2));print('BUILD',name,flush=True)
 with (d/name/'build.log').open('w') as f:
  subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['cmake','--build',str(b),'--target','nethack','-j8'],stdout=f,stderr=subprocess.STDOUT,check=True)
 flags=[]
 for line in (b/'CMakeFiles/nethack.dir/flags.make').read_text().splitlines():
  for prefix in ['C_DEFINES = ','C_INCLUDES = ']:
   if line.startswith(prefix):flags+=shlex.split(line[len(prefix):])
 binary=d/name/'property'
 cmd=['cc','-O2','-g',*flags,'/puffertank/experiments/nethack-compact-state-20261008/fobj_bytes_property.c','-L'+str(b),'-Wl,-rpath,'+str(b),'-lnethack','-o',str(binary)]
 subprocess.run(cmd,check=True)
 with (d/name/'property.log').open('w') as f:subprocess.run([str(binary)],stdout=f,stderr=subprocess.STDOUT,check=True)
 print('PROPERTY',name,(d/name/'property.log').read_text().strip(),flush=True)
assert (d/'control/property.log').read_text()==(d/'candidate/property.log').read_text()
means=[]
for name in ['control','candidate','candidate','control']:
 # Unique run label for every fresh engine snapshot; two restored native trials each.
 k=len(list((r/'native_pool/runs').glob('box_'+name+'_*')))
 label='box_'+name+'_'+str(k)
 print('SCREEN',label,flush=True)
 with (d/(label+'.log')).open('w') as f:
  subprocess.run(['python',str(r/'native_pool/snapshot_test.py'),label,'2048','0:512,0:512','--engine',str(d/name/'build')],stdout=f,stderr=subprocess.STDOUT,check=True)
 x=json.loads((r/'native_pool/runs'/label/'result.json').read_text())
 print('DONE',label,[z['result']['sps'] for z in x['cases']],flush=True)
 means.append(sum(float(z['result']['sps']) for z in x['cases'])/len(x['cases']))
 if len(means)==2 and means[1] < means[0]*1.008:
  print('PARK initial pair below0.8% screening gate; skip longer confirmation.',flush=True)
  break
print('FLOOR BOX SCREEN COMPLETE',flush=True)
