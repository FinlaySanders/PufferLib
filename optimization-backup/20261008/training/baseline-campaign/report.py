from pathlib import Path
import json
r=Path(__file__).parent
rows=json.loads((r/'results.json').read_text())
lines=['# NetHack batching sweep','', 'Mature recorded games; full pipeline with frozen policy weights. See [METHOD.md](METHOD.md) for controls and limitations.','', '| Parameters | Environments | Minibatch | Steps/s | GPU GiB | Rollout tail (s) | PPO tail (s) | Updates/batch |','|---|---:|---:|---:|---:|---:|---:|---:|']
for x in rows:
 p='1.98M' if x['width']==224 else '5.10M'
 if x['rc']==0: lines.append(f"| {p} | {x['agents']} | {x['minibatch']} | {x['sps']:,.0f} | {x['used_mib']/1024:.2f} | {x['rollout_tail']:.3f} | {x['ppo_tail']:.3f} | {x['updates']:.0f} |")
 else: lines.append(f"| {p} | {x['agents']} | {x['minibatch']} | Failed (rc {x['rc']}) | — | — | — | — |")
lines+=['','All successful rows passed three teacher-observation hashes, equality of repeated cohorts, and unchanged initial/final policy parameters. Failures retain logs and command manifests in their case directory.','', 'Timing: six warmed full-pipeline epochs, excluding the final epoch without prefetched rollout. These are short measurements, not confidence intervals. GPU memory includes CUDA context and graph allocations. Larger minibatches reduce optimizer update count and do not establish equal learning quality.']
(r/'REPORT.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
