from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parent
labels = ("priority_live_base", "priority_live_priority")
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
with (root / "priority_live_compare.log").open("w") as output:
    subprocess.run([sys.executable, str(root / "compare_state.py"), *labels],
                   check=True, stdout=output)
numeric = json.loads((root / "runs" / labels[1] /
                      ("compare_" + labels[0] + ".json")).read_text())
result = dict(reference=labels[0], candidate=labels[1], steps=2097152, updates=904,
              checks=checks, finite=all(x["nonfinite"] == 0 for x in numeric.values()),
              exact=all(checks.values()),
              scope="Priority scheduler on the corrected experimental GPU stack; not proof of equivalence between that stack and the original baseline.")
(root / "PRIORITY_LIVE_PROOF.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
assert result["exact"] and result["finite"]
