from pathlib import Path
import json
import sys
import numpy as np

root = Path(__file__).resolve().parent
left, right = [root / 'runs' / x / 'state' for x in sys.argv[1:3]]
results = {}
for a in sorted(left.glob('*.bin')):
    b = right / a.name
    assert b.exists() and a.stat().st_size == b.stat().st_size, a.name
    dtype = np.uint16 if a.name in ('params.bin', 'updates.bin', 'raw_gradients.bin') else np.float32
    x = np.memmap(a, dtype=dtype, mode='r')
    y = np.memmap(b, dtype=dtype, mode='r')
    assert x.size == y.size
    metrics = dict(count=x.size, different=0, nonfinite=0, max_abs=0.0,
        squared_error=0.0, squared_reference=0.0)
    for start in range(0, x.size, 262144):
        xx, yy = x[start:start+262144], y[start:start+262144]
        metrics['different'] += int(np.count_nonzero(xx != yy))
        if dtype == np.uint16:
            xx = (xx.astype(np.uint32) << 16).view(np.float32)
            yy = (yy.astype(np.uint32) << 16).view(np.float32)
        metrics['nonfinite'] += int(np.count_nonzero(~np.isfinite(xx)) + np.count_nonzero(~np.isfinite(yy)))
        diff = yy.astype(np.float64) - xx
        metrics['max_abs'] = max(metrics['max_abs'], float(np.max(np.abs(diff))))
        metrics['squared_error'] += float(np.sum(diff*diff))
        metrics['squared_reference'] += float(np.sum(xx.astype(np.float64)**2))
    metrics['relative_l2'] = (metrics.pop('squared_error') / max(metrics.pop('squared_reference'), 1e-30))**0.5
    results[a.name] = metrics
assert results and all(x['nonfinite'] == 0 for x in results.values()), results
out = right.parent / ('compare_' + left.parent.name + '.json')
out.write_text(json.dumps(results, indent=2))
print(json.dumps(results, indent=2))
