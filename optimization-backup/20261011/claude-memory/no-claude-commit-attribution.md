---
name: no-claude-commit-attribution
description: User wants commits authored solely as themselves, no Co-Authored-By or Claude-Session trailers
metadata:
  type: feedback
---

Commit messages carry only the message the user asked for, no Co-Authored-By / Claude-Session trailers.
**Why:** 2026-09-09 the user said "remove your authorship" after the 'drone release fixes' commit; amended to b52d4e15.
**How to apply:** omit the attribution footer from every commit and PR body in this repo.
