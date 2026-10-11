from pathlib import Path

root = Path(__file__).resolve().parent
prior = root.parent / 'nethack-muon-followups-20261009'
s = (prior / 'run.py').read_text()

def replace(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old)
    s = s.replace(old, new)

replace("parser.add_argument('--profile-matrices',action='store_true')", """parser.add_argument('--profile-matrices',action='store_true')
parser.add_argument('--binary', default=str(root/'binaries/baseline'))
parser.add_argument('--profile', choices=['node','graph'])
parser.add_argument('--end', type=int)
parser.add_argument('--env', action='append', default=[])
""")
replace("command[0] = str(source / 'puffer_followups')", "command[0] = args.binary")
replace("if args.profile_matrices: environment['PUF_MUON_PROFILE']='1'", """if args.profile_matrices: environment['PUF_MUON_PROFILE']='1'
if args.end is not None: environment['BENCH_CAPTURE_END']=str(args.end)
for assignment in args.env:
    key, value = assignment.split('=',1)
    assert key.startswith(('NH_', 'PUF_', 'CUDA_')), key
    environment[key] = value
""")
replace("(directory/'command.json').write_text(json.dumps(manifest, indent=2))", """if args.profile:
    environment['PUF_SIZE_CAPTURE']='1'
    command=['nsys','profile','--trace=cuda,nvtx,osrt','--osrt-threshold=10000',
        '--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi',
        '--capture-range-end=stop','--cuda-graph-trace='+args.profile,
        '--wait=all','--kill=none','--output='+str(directory/'timeline'),*command]
    manifest['environment_overrides']['PUF_SIZE_CAPTURE']='1'
    manifest['command']=command
manifest['profile']=args.profile
(directory/'command.json').write_text(json.dumps(manifest, indent=2))""")
replace("log=(directory/'run.log').read_text(errors='replace')", """if rc == 0 and args.profile:
    with (directory/'export.log').open('w') as export:
        subprocess.run(['nsys','export','--type=sqlite','--output='+str(directory/'timeline.sqlite'),str(directory/'timeline.nsys-rep')],stdout=export,stderr=subprocess.STDOUT,check=True)
log=(directory/'run.log').read_text(errors='replace')""")
replace("result={'label':args.label", "result={'profile':args.profile,'label':args.label")
(root / 'run.py').write_text(s)
