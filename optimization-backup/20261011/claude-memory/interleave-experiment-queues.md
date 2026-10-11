---
name: interleave-experiment-queues
description: Order GPU queues so paired/usable reads complete incrementally — experiments must be stoppable at any time with results intact
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-29T20:32:51.589Z
---

The user wants experiment queues ordered so that a usable result unit (a completed pair, a finished cell) lands after nearly every run — "I want things interleaved so we can stop experiments at any time and move on" (2026-08-29, deep-vs-fused 1B queue).

**Why:** queues get killed mid-flight constantly in this campaign (user redirects several times a day); a queue that runs all of arm A before arm B leaves nothing comparable when stopped early.

**How to apply:** (1) pair new runs against already-banked runs first (those complete a pair immediately); (2) for fresh seeds, alternate arms per seed — and the EXPERIMENTAL arm runs FIRST in each pair, so it is never behind the control at any stop point (user corrected a queue that ran control-first, 2026-08-29); (3) put optional/validation cells last; (4) when reporting the queue, show what's in hand at each stop point. Related: [[supervised-probes-before-runs]], [[no-checkpoint-forking]].
