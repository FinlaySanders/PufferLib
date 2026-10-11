from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parent
if len(sys.argv) != 4:
    raise SystemExit("usage: validate_live.py REFERENCE CANDIDATE OUTPUT_JSON")
labels = tuple(sys.argv[1:3])
output_path = Path(sys.argv[3])
rows = [json.loads((root / "runs" / label / "result.json").read_text())
        for label in labels]
expected_rollouts = {
    "observations", "actions", "values", "logprobs", "rewards", "terminals",
    "action_mask", "initial_states", "env_obs", "state0", "state1", "state2", "state3",
}
for label, result in zip(labels, rows):
    command = json.loads((root / "runs" / label / "command.json").read_text())
    env = command["environment_overrides"]
    assert "PUF_ACTION_REPLAY" not in env and "PUF_PERF_FREEZE" not in env
    assert env["PUF_LIVE_AFTER_WARM"] == "1"
    assert result["rc"] == 0 and len(result["epochs"]) == 8
    assert result["initial_sha"] != result["final_sha"], "Updates must be applied"
    assert result["ages"][-1]["steps"] == 2097152
    assert all(x["batch"] == 262144 and x["mb"] == 4096 and x["updates"] == 113
               for x in result["epochs"])
    assert {line.split()[0] for line in result["rollout_hashes"].splitlines()} == expected_rollouts
    assert set(result["state_hashes"]) == {"master.bin", "momentum.bin", "updates.bin"}

checks = {key: rows[0][key] == rows[1][key]
          for key in ("initial_sha", "final_sha", "rollout_hashes", "state_hashes")}
with (output_path.with_suffix(".compare.log")).open("w") as output:
    subprocess.run([sys.executable, str(root / "compare_state.py"), *labels],
                   check=True, stdout=output)
numeric = json.loads((root / "runs" / labels[1] /
                      ("compare_" + labels[0] + ".json")).read_text())
result = dict(reference=labels[0], candidate=labels[1], steps=2097152, updates=904,
              checks=checks, finite=all(x["nonfinite"] == 0 for x in numeric.values()),
              exact=all(checks.values()),
              scope="Final state and rollout buffers after 904 applied updates with live actions; not a hash of every intermediate step, and not a proof of equal long-run learning across numerically different stacks.",
              coverage="Final two-slot rollout fields, environment observations, per-buffer RNN states, weights, momentum and update buffers.")
output_path.write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
assert result["exact"] and result["finite"]
