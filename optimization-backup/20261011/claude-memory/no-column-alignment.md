---
name: no-column-alignment
description: "User dislikes column-aligned assignments/comments in code — keep operators flush, single space"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
  modified: 2026-08-01T14:52:48.090Z
---

The user rejected column alignment in `nethack_add_log` twice: first the
mixed alignment, then my fix that aligned everything ("no i dont like
alignment, they should just be flush").

**Why:** alignment is maintenance noise — adding a longer name re-ripples
every line; flush single-space never churns.

**How to apply:** write `x += y;` with single spaces, never pad names or
operators into columns, even when nearby upstream code is aligned. Related:
[[minimal-code-comments]].
