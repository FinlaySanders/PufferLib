---
name: clear-question-before-build
description: Every build/run must be preceded by an explicit falsifiable question; no reflexive arms
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-30T20:42:00.051Z
---

Before building any new arm or queueing any run, state the precise question it answers, the decision rule for reading the result, and check the question's PREMISE is already established (don't build follow-ons to unconfirmed n=1 effects).

**Why:** 2026-08-31 the user stopped an overnight queue: I had built NH_BINIT2 and queued binit-family 1B cells before the +775 binit effect itself was confirmed (n=1) — follow-on arms to an unestablished premise. "Before we build anything, we need a clear question we want to answer."

**How to apply:** For each proposed cell write: Q (falsifiable), decision rule (what result means what), premise (what must already be true). Make queues conditional on premise-establishing cells where possible. Related: [[supervised-probes-before-runs]], [[interleave-experiment-queues]], [[no-hand-edited-hypers]].
