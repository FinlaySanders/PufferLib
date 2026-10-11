# Replacement identity behavioural audit and frozen probes

Two policies: replacement 1B s701 (NH_DISC_SWAP=1) and prior additive 1B s701 (NH_DISC_SWAP=0). Same eval seed 7; 512 agents; 14,000 completed episodes per policy, dropping the first 4,000 and retaining the next 10,000. No additional RL training.

The isolated engine logs ring, amulet and scroll acquisition/availability, public type knowledge, actual jewellery equip/unequip transitions, exact scroll consumption, and identification targets. Jewellery successes are setworn transitions under PUTON, not command submissions. Initial equipment is not counted as a policy equip. Availability is inventory presence at policy boundaries, not guaranteed action eligibility. True types are for the audit only and are never passed to the policy. Acquisition delays on merged stacks do not identify individual copies. Existing source and active training engine are unchanged.

After both certificates, replacement-probes/fit.py fits linear and 128-unit MLP readouts on frozen encoders from both policies. Targets are known ring, amulet and scroll identity before ReLU, after ReLU and after pooled inventory encoding. Same synthetic identity/appearance pairs, state templates, held-out splits and two probe seeds. Learning rate and stopping use validation loss, not test accuracy. The C forward and extracted-weight reconstruction agree within 1e-5 for both checkpoints.

Replacement guarantees known-item appearance invariance by construction; stronger identity readout alone does not demonstrate improved decision making. Availability-conditioned equip/consumption rates test behaviour separately.
