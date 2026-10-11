#!/usr/bin/env python3
"""Snapshot completed certs, then reproduce article statistics from hashed inputs."""
import argparse
import base64
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics as st
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
LANES = {"1B": ["fixwt1b_s701", "fixwt1b_s702"],
         "2B": ["fixwt2b_s703", "fixwt2b_s704"],
         "4B": ["fixwt4b_s705", "fixwt4b_s706"]}
STEPS = {"1B": 999817216, "2B": 1999896576, "4B": 3999793152}


def specs():
    out = []
    for size, lanes in LANES.items():
        for lane in lanes:
            for interface, seeds in (("fork", [7]), ("stock", [21, 32] if size != "4B" else [21]), ("gym", [None])):
                for seed in seeds:
                    rid = f"r4_{lane}_4k" if interface == "gym" else f"{interface}_{lane}_s{seed}"
                    out.append(dict(id=rid, size=size, lane=lane, training_seed=int(lane[-3:]),
                                    interface=interface, eval_seed=seed, cohort="headline",
                                    checkpoint_steps=STEPS[size],
                                    checkpoint_path=f"/workspace/sweeps/nhfix/checkpoints/nethack/{lane}/{STEPS[size]:016d}.bin"))
            if size != "4B":
                out.append(dict(id=f"r4_{lane}", size=size, lane=lane, training_seed=int(lane[-3:]),
                                interface="gym", eval_seed=None, cohort="historical_480",
                                checkpoint_steps=STEPS[size], checkpoint_path=None))
    return out


def sha(data):
    return hashlib.sha256(data).hexdigest()


def refresh():
    old_path = ROOT/'manifest.json'
    old_runs = {r['id']: r for r in json.loads(old_path.read_text())['runs']} if old_path.exists() else {}
    # Remote code only reads whitelisted result files, launch scripts and checkpoints.
    remote = r'''
import pathlib, json, base64, hashlib, re
root = pathlib.Path('/workspace/sweeps/certq/equiv')
log = (root/'equiv.log').read_text()
out = {'log': log, 'runs': {}, 'scripts': {}, 'checkpoints': {}}
for size, seeds in ((1,[701,702]),(2,[703,704]),(4,[705,706])):
 for seed in seeds:
  lane = f'fixwt{size}b_s{seed}'
  steps = {1:999817216,2:1999896576,4:3999793152}[size]
  cp = pathlib.Path(f'/workspace/sweeps/nhfix/checkpoints/nethack/{lane}/{steps:016d}.bin')
  if cp.exists(): out['checkpoints'][lane] = hashlib.sha256(cp.read_bytes()).hexdigest()
  ids = [f'fork_{lane}_s7'] + [f'stock_{lane}_s{s}' for s in ([21,32] if size != 4 else [21])] + [f'r4_{lane}_4k']
  for rid in ids:
   starts = [x for x in log.splitlines() if f' START {rid} ' in x]
   dones = [x for x in log.splitlines() if f' DONE {rid} ' in x]
   d = {'start': starts[-1] if starts else None, 'done': dones[-1] if dones else None, 'files': {}}
   if dones and (rid.startswith('r4_') or ' rc=0 ' in dones[-1]):
    paths = sorted((root/rid).glob('w*.jsonl')) if rid.startswith('r4_') else [root/(rid+'.ep')]
    for p in paths:
     if p.exists(): d['files'][str(p.relative_to(root))] = base64.b64encode(p.read_bytes()).decode()
   out['runs'][rid] = d
for name in ['nh_certq_fix.sh','nh_certq_extra.sh','nh_gym4k.sh','nh_gym4k_12b.sh','nh_fixwt.sh']:
 p = pathlib.Path('/workspace/sweeps')/name
 if p.exists(): out['scripts'][name] = p.read_text()
print(json.dumps(out))
'''
    proc = subprocess.run(["ssh", "-o", "ConnectTimeout=15", "drone", "python3 -"],
                          input=remote, text=True, capture_output=True, check=True)
    payload = json.loads(proc.stdout)
    now = datetime.now(timezone.utc).isoformat()
    manifest = dict(schema_version=1, snapshot_utc=now, runs=[], evidence=[])

    def snapshot(rel, data, source):
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return dict(path=rel, sha256=sha(data), bytes=len(data), source=source)

    manifest['evidence'].append(snapshot('evidence/equiv.log', payload['log'].encode(),
                                        'drone:/workspace/sweeps/certq/equiv/equiv.log'))
    for name, content in payload['scripts'].items():
        manifest['evidence'].append(snapshot('evidence/'+name, content.encode(), 'drone:/workspace/sweeps/'+name))
    for run in specs():
        run['files'] = []
        run['checkpoint_sha256_at_snapshot'] = payload['checkpoints'].get(run['lane'])
        if run['cohort'] == 'historical_480':
            directory = Path('/tmp/reg') / run['id']
            for path in sorted(directory.glob('w*.jsonl')):
                run['files'].append(snapshot('raw/'+run['id']+'/'+path.name, path.read_bytes(), 'local:'+str(path)))
            if not run['files'] and run['id'] in old_runs:
                run['files'] = old_runs[run['id']]['files']
            run['provenance_note'] = 'Earlier local 24x20 worker records; retained checkpoint hash is not a launch-time identity check.'
        else:
            remote_run = payload['runs'][run['id']]
            run['start_evidence'] = remote_run['start']
            run['done_evidence'] = remote_run['done']
            for rel, encoded in remote_run['files'].items():
                run['files'].append(snapshot('raw/'+rel, base64.b64decode(encoded),
                                            'drone:/workspace/sweeps/certq/equiv/'+rel))
        run['availability'] = 'snapshotted' if run['files'] else 'pending_or_missing'
        manifest['runs'].append(run)
    (ROOT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return build()


def stats(scores):
    values = sorted(scores)
    n = len(values)
    if not n:
        raise ValueError('empty score selection')
    out = dict(n=n, mean=st.mean(values), se=st.pstdev(values)/math.sqrt(n),
               median=st.median(values), max=values[-1])
    for p in (10, 25, 75, 90, 99):
        out['p'+str(p)] = values[min(n-1, int(p*n/100))]
    out['quant'] = [values[int(k/63*(n-1))] for k in range(64)]
    return out


def read_checked(file):
    data = (ROOT/file['path']).read_bytes()
    if sha(data) != file['sha256']:
        raise ValueError('hash mismatch: '+file['path'])
    return data.decode()


def scores_for(run):
    if not run['files']:
        return None, dict(status='pending_or_missing')
    if run['interface'] == 'gym':
        workers, k = (144, 28) if run['cohort'] == 'headline' else (24, 20)
        expected = {f'w{i}.jsonl' for i in range(1, workers+1)}
        actual = {Path(f['path']).name for f in run['files']}
        if actual != expected:
            raise ValueError(f"{run['id']}: expected {workers} distinct workers, got {len(actual)}")
        if len(run['files']) != workers:
            raise ValueError('Duplicate worker file: '+run['id'])
        rows = []
        for f in run['files']:
            worker = [json.loads(line) for line in read_checked(f).splitlines() if line.strip()]
            if len(worker) != k or [r['ep'] for r in worker] != list(range(1, k+1)):
                raise ValueError(f"{f['path']}: incomplete/duplicated worker episodes")
            rows.extend(worker)
        statuses = {str(s): sum(r['end_status'] == s for r in rows) for s in sorted({r['end_status'] for r in rows})}
        return [r['env_score'] for r in rows], dict(status='validated', raw_n=len(rows),
                    discarded_n=0, workers=workers, episodes_per_worker=k, end_status_counts=statuses)
    if len(run['files']) != 1:
        raise ValueError('Expected one episode file: '+run['id'])
    rows = [line.split() for line in read_checked(run['files'][0]).splitlines() if line.strip()]
    target = 14000 if run['interface'] == 'fork' else 10000
    if len(rows) < target:
        raise ValueError(f"{run['id']}: {len(rows)} rows, expected at least {target}")
    match = re.search(r'\beps=(\d+)', run.get('done_evidence') or '')
    if not match or int(match[1]) != len(rows):
        raise ValueError('DONE count differs from raw data: '+run['id'])
    kept = rows[4000:14000]
    return [int(r[0]) for r in kept], dict(status='validated', raw_n=len(rows), discarded_n=4000,
                overshoot_excluded=max(0, len(rows)-14000), selection='rows[4000:14000]')


def build():
    manifest = json.loads((ROOT/'manifest.json').read_text())
    for f in manifest['evidence']:
        read_checked(f)
    result = dict(schema_version=1, snapshot_utc=manifest['snapshot_utc'],
                  manifest_sha256=sha((ROOT/'manifest.json').read_bytes()), runs=[], gens={})
    all_scores = {}
    for run in manifest['runs']:
        scores, validation = scores_for(run)
        row = {k: run[k] for k in ('id','size','lane','interface','eval_seed','cohort')}
        row.update(validation)
        row['stats'] = stats(scores) if scores is not None else None
        result['runs'].append(row)
        all_scores[run['id']] = scores
    for size in LANES:
        result['gens'][size] = {}
        for interface in ('fork','stock','gym'):
            runs = [r for r in result['runs'] if r['size']==size and r['interface']==interface and r['cohort']=='headline']
            complete = all(r['stats'] is not None for r in runs)
            pooled = stats([s for r in runs for s in all_scores[r['id']]]) if complete else None
            result['gens'][size][interface] = dict(status='complete' if complete else 'pending',
                        run_ids=[r['id'] for r in runs], runs=[dict(r['stats'], run=r['id']) for r in runs if r['stats']], pooled=pooled)
    (ROOT/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    fields = ['size','interface','run','status','n','mean','se','median','p10','p25','p75','p90']
    with (ROOT/'results.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for r in result['runs']:
            writer.writerow(dict(size=r['size'], interface=r['interface'], run=r['id'], status=r['status'], **(r['stats'] or {})))
        for size, interfaces in result['gens'].items():
            for interface, group in interfaces.items():
                writer.writerow(dict(size=size, interface=interface, run='pooled_headline', status=group['status'], **(group['pooled'] or {})))
    lines = ['# Fixed-model evaluation results', '', 'Snapshot (UTC): '+result['snapshot_utc'], '',
             'Generated from hashed raw episode records. See [protocol and limitations](README.md).', '',
             '| Steps | Interface | Games | Mean | Mean SE | Median |',
             '|---|---|---:|---:|---:|---:|']
    for size, interfaces in result['gens'].items():
        for interface, group in interfaces.items():
            p = group['pooled']
            lines.append(f"| {size} | {interface} | {p['n']:,} | {p['mean']:,.1f} | {p['se']:,.1f} | {p['median']:,.1f} |" if p else f'| {size} | {interface} | pending complete pair | — | — | — |')
    lines += ['', '## Individual certificates', '', '| Run | Status | Games | Mean | Median |', '|---|---|---:|---:|---:|']
    for r in result['runs']:
        p = r['stats']
        label = r['id'] + (' (historical 480)' if r['cohort']=='historical_480' else '')
        lines.append(f"| {label} | {r['status']} | {p['n']:,} | {p['mean']:,.1f} | {p['median']:,.1f} |" if p else f"| {label} | {r['status']} | — | — | — |")
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines[:16]))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['refresh','build'])
    args = parser.parse_args()
    refresh() if args.command == 'refresh' else build()
