from pathlib import Path
import json
import os
import re
import sys
import time

root = Path(__file__).resolve().parent
pending = set(sys.argv[1:])
hz = os.sysconf('SC_CLK_TCK')
deadline = time.monotonic() + 900

def snapshot(proc):
    out = {}
    for task in (proc / 'task').iterdir():
        try:
            fields = (task / 'stat').read_text().rsplit(')', 1)[1].split()
            out[int(task.name)] = int(fields[11]) + int(fields[12])
        except FileNotFoundError:
            pass
    return out

while pending and time.monotonic() < deadline:
    try:
        active = json.loads((root / 'ACTIVE.json').read_text())
        label = active.get('label')
        proc = Path('/proc') / str(active.get('pid', 0))
        if label not in pending or not proc.exists():
            time.sleep(.25)
            continue
        cmdline = (proc / 'cmdline').read_bytes()
        assert str(root / 'binaries').encode() in cmdline
        log = root / 'runs' / label / 'run.log'
        before = None
        while proc.exists():
            with log.open('rb') as f:
                f.seek(max(0, log.stat().st_size-32768))
                text = f.read().decode(errors='replace')
            epochs = re.findall(r'BATCH_PERF epoch=(\d+)', text)
            epoch = int(epochs[-1]) if epochs else -1
            if epoch >= 64 and before is None:
                before = snapshot(proc)
                start = time.monotonic()
                first_epoch = epoch
            if epoch >= 78 and before is not None:
                after = snapshot(proc)
                elapsed = time.monotonic() - start
                rows = [dict(tid=k, cpu_percent=100*(v-before[k])/hz/elapsed)
                    for k,v in sorted(after.items()) if k in before]
                result = dict(label=label, pid=active['pid'], first_epoch=first_epoch,
                    last_epoch=epoch, elapsed=elapsed, threads=rows,
                    total_cpu_percent=sum(x['cpu_percent'] for x in rows))
                (log.parent / 'cpu_mature.json').write_text(json.dumps(result, indent=2))
                print(json.dumps(dict(label=label, main=rows[0]['cpu_percent'],
                    total=result['total_cpu_percent'], epochs=[first_epoch,epoch])), flush=True)
                break
            time.sleep(.25)
        pending.remove(label)
    except (FileNotFoundError, json.JSONDecodeError):
        time.sleep(.25)
assert not pending, pending
