from pathlib import Path
import bisect
import collections
import csv
import json
import sqlite3
import statistics
import sys

root = Path(__file__).resolve().parent
directory = root / 'runs' / sys.argv[1]
db = sqlite3.connect(directory / 'timeline.sqlite')
db.row_factory = sqlite3.Row
names = dict(db.execute('select id,value from StringIds'))
nvtx = list(db.execute('select start,end,globalTid,text,textId from NVTX_EVENTS order by start'))
ranges = collections.defaultdict(list)
for r in nvtx:
    name = r['text'] or names.get(r['textId'])
    if name in ('train_forward_backward', 'rollout.gpu_submit') and r['end'] is not None:
        ranges[r['globalTid']].append((r['start'], r['end'], name))
starts = {tid: [r[0] for r in rows] for tid, rows in ranges.items()}
tags, apis = {}, {}
for r in db.execute('select * from CUPTI_ACTIVITY_KIND_RUNTIME order by start'):
    rows = ranges[r['globalTid']]
    i = bisect.bisect_right(starts.get(r['globalTid'], []), r['start']) - 1
    tag = 'other'
    if i >= 0 and rows[i][1] >= r['start']:
        tag = 'ppo' if rows[i][2] == 'train_forward_backward' else 'inference'
    tags[r['correlationId']] = tag
    apis[r['correlationId']] = dict(r)

kernels = list(db.execute('select start,end,streamId,correlationId,demangledName from CUPTI_ACTIVITY_KIND_KERNEL order by start'))
# Muon spans all optimizer streams. A per-stream switch misses side-stream GEMMs.
opt_starts, opt_ends = [], []
for r in kernels:
    if tags.get(r['correlationId']) != 'ppo': continue
    name = names[r['demangledName']]
    if name.startswith('muon_sum_sq_partials'): opt_starts.append(r['start'])
    if name.startswith('muon_weight_update'): opt_ends.append(r['end'])
assert len(opt_starts) == len(opt_ends), (len(opt_starts), len(opt_ends))
totals = collections.Counter()
counts = collections.Counter()
groups = collections.defaultdict(lambda: collections.Counter())
spans = {}
for r in kernels:
    corr = r['correlationId']
    tag = tags.get(corr, 'other')
    if tag == 'ppo':
        i = bisect.bisect_right(opt_starts, r['start']) - 1
        tag = 'optimizer' if i >= 0 and r['start'] <= opt_ends[i] else 'forward_loss_backward'
    name = names[r['demangledName']]
    ns = r['end'] - r['start']
    totals[tag] += ns
    groups[tag][name] += ns
    counts[tag, name] += 1
    if corr not in spans: spans[corr] = [r['start'], r['end'], r['streamId']]
    else:
        spans[corr][0] = min(spans[corr][0], r['start'])
        spans[corr][1] = max(spans[corr][1], r['end'])

def distribution(xs):
    if not xs: return None
    xs = sorted(xs)
    return dict(n=len(xs), mean_ms=statistics.mean(xs), median_ms=statistics.median(xs),
                p99_ms=xs[int(.99 * (len(xs)-1))], max_ms=max(xs))

uploads = collections.defaultdict(list)
for r in db.execute('select streamId,end from CUPTI_ACTIVITY_KIND_MEMCPY where copyKind=1 order by end'):
    uploads[r['streamId']].append(r['end'])
execution, submitted_wait, input_ready_wait = [], [], []
for corr, (start, end, stream) in spans.items():
    api = apis.get(corr)
    if not api or tags.get(corr) != 'inference' or 'cudaGraphLaunch' not in names[api['nameId']]: continue
    execution.append((end-start)/1e6)
    submitted_wait.append(max(0, start-api['end'])/1e6)
    ups = uploads[stream]
    i = bisect.bisect_right(ups, start)-1
    if i >= 0:
        input_ready_wait.append(max(0, start-max(api['end'], ups[i]))/1e6)

cpu = {}
for tag in ('rollout.gpu_wait','rollout.env','rollout.gpu_submit','rollout.upload','pool.tail_wait'):
    cpu[tag] = distribution([(r['end']-r['start'])/1e6 for r in nvtx
        if r['end'] is not None and (r['text'] or names.get(r['textId'])) == tag])

output = dict(kernel_seconds={k:v/1e9 for k,v in totals.items()},
    summed_kernel_percent={k:100*v/sum(totals.values()) for k,v in totals.items()},
    optimizer_updates=len(opt_starts), inference_execution=distribution(execution),
    inference_wait_since_submission=distribution(submitted_wait),
    inference_wait_after_upload_and_submission=distribution(input_ready_wait), cpu_ranges=cpu,
    top_by_group={group:[dict(name=name, summed_ms=ns/1e6, calls=counts[group,name],
        mean_us=ns/counts[group,name]/1e3) for name,ns in rows.most_common(15)] for group,rows in groups.items()},
    method='Summed kernel durations are not additive wall time. Optimizer intervals span all training streams; inference is identified from graph-launch thread/NVTX correlation. Graph execution spans first to last kernel and includes internal gaps. Input-ready wait uses the last preceding H2D completion on that stream and the end of the launch API; dependencies beyond these are not proven ready. Nsight node tracing adds overhead; do not use profiled SPS as throughput.')
(directory / 'profile.json').write_text(json.dumps(output, indent=2))
with (directory / 'kernels.csv').open('w') as f:
    w = csv.writer(f); w.writerow(['group','kernel','calls','summed_ms','mean_us'])
    for group,rows in groups.items():
        for name,ns in rows.most_common(): w.writerow([group,name,counts[group,name],ns/1e6,ns/counts[group,name]/1e3])
print(json.dumps({k:v for k,v in output.items() if k != 'top_by_group'},indent=2))
print('Top inference kernels:')
for row in output['top_by_group'].get('inference',[]): print(row)
