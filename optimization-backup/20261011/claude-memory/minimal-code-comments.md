---
name: minimal-code-comments
description: "User dislikes extraneous code comments — very brief one-liners at most, often none"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0659b524-7c59-4516-a2bf-e5c47f427d6d
---

Finlay: "i dont like extraneous comments. they should be very very brief if present at all."

**Why:** Multi-line explanatory comments I added to a pufferlib.cu fix (explaining CUDA graph capture semantics) were too verbose for his taste, even for a PR aimed at reviewers unfamiliar with the subtlety.

**How to apply:** Default to no comment. When a constraint genuinely can't be seen from the code (e.g. "device ptr: by-value args get baked into the cuda graph"), use a single short trailing or one-line comment. Never multi-line comment blocks. Comments should say what the code *does*, not justify a design choice — he rejected "// unconditional: the kernel reads this even with annealing off" in favor of "// copy ent_coef to the device buffer read by the loss kernel".
