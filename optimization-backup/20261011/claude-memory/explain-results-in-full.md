---
name: explain-results-in-full
description: "After each analysis, explain the results and their meaning in plain terms — don't just log to ledger and move on"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a05ccdbb-322b-4b8a-8e6b-e69d4a0642b6
  modified: 2026-08-30T13:09:24.379Z
---

2026-08-30, after a run of dense interp analyses: "Explain the results to me. You keep doing analysis then not sharing the results."

**Why:** ledger appends and compressed jargon tables are for memory, not communication. The user wants each analysis followed by a plain-language account of what was found and what it means for the live question — complete sentences, numbers explained in context, the "so what" stated explicitly.

**How to apply:** after any analysis lands, the next message leads with a self-contained explanation: the question, what the experiment showed, what it means, what's still open. Write for a colleague catching up, not for the ledger. Tables support prose, never replace it. Related: [[interleave-experiment-queues]].
