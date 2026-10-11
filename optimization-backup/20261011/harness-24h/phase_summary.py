"""Align post-train detail counters with zero-based outer-loop SPS epochs."""
from pathlib import Path
import collections
import json
import re
import statistics
import sys

root = Path(__file__).resolve().parent
path = Path(sys.argv[1])
output = []
for run in json.loads(path.read_text()):
    groups = collections.defaultdict(list)
    for line in (root / "runs" / run["label"] / "run.log").read_text().splitlines():
        if not line.startswith(("ROLLOUT_DETAIL ", "POOL_TIMING ")):
            continue
        row = {k: float(v) for k, v in re.findall(r"(\w+)=([-+0-9.eE]+)", line)}
        # train_impl increments pufferl->epoch before rollout_finish logs details.
        row["loop_epoch"] = row["epoch"] - 1
        if 64 <= row["loop_epoch"] < 79:
            groups[line.split()[0]].append(row)
    summaries = {}
    for tag, rows in groups.items():
        assert len(rows) == 60, (run["label"], tag, len(rows))
        fields = [k for k in rows[0] if k not in ("epoch", "loop_epoch", "buffer")]
        if tag == "POOL_TIMING":
            assert all(row["samples"] == 128 for row in rows)
        summaries[tag] = dict(
            means={k: statistics.mean(row[k] for row in rows) for k in fields},
            by_buffer={str(b): {k: statistics.mean(row[k] for row in rows if row["buffer"] == b)
                               for k in fields} for b in range(4)},
        )
    output.append(dict(label=run["label"], sps=run["sps"], phases=summaries))

result = dict(rows=output, loop_epoch_window=[64, 78], detail_epoch_window=[65, 79],
              caveat="Per-buffer stages overlap across buffers and are not additive pipeline wall time.")
target = path.with_name(path.name.replace(".results.json", "_PHASES.json"))
target.write_text(json.dumps(result, indent=2))
for row in output:
    print(row["label"], {tag: data["means"] for tag, data in row["phases"].items()})
