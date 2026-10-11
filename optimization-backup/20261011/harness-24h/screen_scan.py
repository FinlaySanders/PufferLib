from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parent
binary = root/'binaries/fused_scan_v3'
jobs = [('encoder', 'encoder_fused_a', {'NH_FUSED_BR': 1}),
        ('time', 'scan_gpu_base_a', {}),
        ('time', 'scan_gpu_forward', {'PUF_SCAN_ROW': 1}),
        ('time', 'scan_gpu_backward', {'PUF_SCAN_ROW': 2}),
        ('time', 'scan_gpu_both', {'PUF_SCAN_ROW': 3}),
        ('time', 'scan_gpu_base_b', {})]
results = []
for kind, label, overrides in jobs:
    command = [sys.executable, str(root/'run.py'), kind, label,
               '--binary='+str(binary), '--trials=6']
    command += ['--env='+k+'='+str(v) for k,v in overrides.items()]
    print('START', label, flush=True)
    with (root/(label+'.launcher.log')).open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = json.loads((root/'runs'/label/'result.json').read_text())
    results.append(result)
    (root/'SCAN_SCREEN.json').write_text(json.dumps(results, indent=2))
    print('DONE', label, result.get('mean_ms'), flush=True)
