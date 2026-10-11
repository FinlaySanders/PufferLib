"""Cheap correctness gate, then fresh interleaved native timing."""
from pathlib import Path
import json
import os
import statistics
import subprocess
import sys
import time

R = Path(__file__).resolve().parent
D = R / 'liquid_fastpath'
OLD = Path('/puffertank/experiments/nethack-compact-state-20261008')
envs = int(sys.argv[1]) if len(sys.argv) > 1 else 512
assert envs in (512, 2048)
if envs == 512:
    clean = {k: v for k, v in os.environ.items()
             if not k.startswith(('NH_', 'NLE_', 'OMP_', 'PUF_', 'PUFFER_', 'CPU_'))
             and k not in ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'NETHACKOPTIONS')}
    clean.update(NETHACKDIR='/puffertank/experiments/nethack-perf-20260917/dat', NH_ZT_MASK='0')
    checks = []
    for label, count in [('goldens', 34), ('fuzz', 26)]:
        fixtures = sorted(map(str, (OLD / 'checks' / label).glob('*.golden')))
        assert len(fixtures) == count
        cmd = ['/puffertank/experiments/nethack-perf-20260917/gates/replay_golden',
               str(D / 'build/libnethack.so'), clean['NETHACKDIR'], *fixtures]
        start = time.monotonic()
        with (D / (label + '.log')).open('w') as log:
            p = subprocess.run(cmd, env=clean, stdout=log, stderr=subprocess.STDOUT)
        checks.append(dict(label=label, count=count, rc=p.returncode,
                           seconds=time.monotonic()-start, command=cmd))
        (D / 'SMOKE.json').write_text(json.dumps(checks, indent=2))
        assert p.returncode == 0, (D / (label + '.log')).read_text()[-3000:]
        print('PASS', label, flush=True)

sys.path.insert(0, str(R / 'native_pool'))
from snapshot_test import run
steps = 2048 if envs == 512 else 512
rows = []
for role, engine in [('base_a', R / 'floor_empty_base/build'),
                     ('candidate_a', D / 'build'), ('candidate_b', D / 'build'),
                     ('base_b', R / 'floor_empty_base/build')]:
    row = run(f'liquid_fastpath_{envs}_{role}', envs, f'0:{steps},0:{steps}',
              engine=engine, workers=32, pin=False)
    row['role'] = role
    rows.append(row)
    (D / f'SCREEN_{envs}.json').write_text(json.dumps(rows, indent=2))
base = [float(c['result']['sps']) for row in rows if row['role'].startswith('base') for c in row['cases']]
candidate = [float(c['result']['sps']) for row in rows if row['role'].startswith('candidate') for c in row['cases']]
endpoints = {(c['result']['obs'], c['result']['turns'], c['result']['age'])
             for row in rows for c in row['cases']}
assert len(endpoints) == 1
summary = dict(control_sps=statistics.mean(base), candidate_sps=statistics.mean(candidate),
               gain_percent=100*(statistics.mean(candidate)/statistics.mean(base)-1),
               control_drift_percent=100*(statistics.mean(base[2:])/statistics.mean(base[:2])-1),
               control_values=base, candidate_values=candidate, endpoints_exact=True,
               scope='Ordinary LTO native screen; not a full-training speedup or broad correctness proof.')
(D / f'SCREEN_{envs}_SUMMARY.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2), flush=True)
