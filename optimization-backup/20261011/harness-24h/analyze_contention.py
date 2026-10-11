"""Partition trace latencies by overlap with the recorded PPO graph spans.

This is descriptive: the phases also differ in buffer readiness and game state.
Nsight node tracing perturbs execution; these are not throughput benchmarks.
"""
from pathlib import Path
import bisect
import collections
import json
import runpy
import sys

root = Path(__file__).resolve().parent
g = runpy.run_path(str(root / "analyze_profile.py"))
directory = g["directory"]
spans, tags, apis, names = (g[k] for k in ("spans", "tags", "apis", "names"))


def union(intervals):
    result = []
    for start, end in sorted(intervals):
        if result and start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])
    return result


training = union((start, end) for corr, (start, end, _) in spans.items()
                 if tags.get(corr) == "ppo")
starts = [x[0] for x in training]


def overlap(start, end):
    i = max(0, bisect.bisect_right(starts, start) - 1)
    total = 0
    while i < len(training) and training[i][0] < end:
        a, b = training[i]
        total += max(0, min(b, end) - max(a, start))
        i += 1
    return total


def phase(start, end):
    if end <= start:
        return "empty"
    fraction = overlap(start, end) / (end - start)
    return ("training_overlap" if fraction >= .95 else
            "no_training_overlap" if fraction == 0 else "mixed")


rows = collections.defaultdict(lambda: collections.defaultdict(list))
kernel_time = collections.Counter()
for kernel in g["kernels"]:
    kernel_time[kernel["correlationId"]] += kernel["end"] - kernel["start"]
for corr, (start, end, stream) in spans.items():
    api = apis.get(corr)
    if tags.get(corr) != "inference" or not api:
        continue
    if "cudaGraphLaunch" not in names[api["nameId"]]:
        continue
    group = rows[phase(start, end)]
    group["inference_graph_span_ms"].append((end - start) / 1e6)
    group["inference_summed_kernel_ms"].append(kernel_time[corr] / 1e6)
    group["wait_after_submit_ms"].append(max(0, start - api["end"]) / 1e6)

cpu_names = ("rollout.env", "rollout.gpu_wait", "rollout.gpu_submit",
             "rollout.upload", "pool.tail_wait", "pool.reader_drain",
             "pool.submitter_work", "pool.worker_work")
for row in g["nvtx"]:
    name = row["text"] or names.get(row["textId"])
    if name not in cpu_names or row["end"] is None:
        continue
    rows[phase(row["start"], row["end"])][name + "_ms"].append(
        (row["end"] - row["start"]) / 1e6)

result = {
    "training_span_count": len(training),
    "training_span_seconds": sum(b-a for a, b in training) / 1e9,
    "groups": {name: {metric: g["distribution"](values)
                      for metric, values in metrics.items()}
               for name, metrics in rows.items()},
    "limitations": [
        "Overlap is with first-to-last-kernel PPO graph spans, including gaps.",
        "Phase groups are observational, not controlled causal estimates.",
        "Node tracing adds overhead; use unprofiled full runs for SPS.",
        "Concurrent CPU ranges and kernel durations cannot be added as wall time.",
    ],
}
(directory / "contention.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
