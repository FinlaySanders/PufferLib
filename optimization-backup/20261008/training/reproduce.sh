#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
label="${1:-reproduce}"
python "$root/bench_extra.py" "$label-base" /puffertank/experiments/nethack-batch-sweep-20260918/source/puffer_batch
python "$root/bench_extra.py" "$label-retained" "$root/retained/puffer_retained"
python "$root/bench_extra.py" "$label-update" "$root/retained/puffer_retained" --update --env="PUF_STATE_PROOF=$root/$label-update"
