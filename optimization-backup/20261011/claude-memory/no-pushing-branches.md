---
name: no-pushing-branches
description: The user pushes branches and opens PRs themselves; I prepare local commits only (2026-09-13)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 05e05423-48d5-4412-9e03-4ac5748e3a83
  modified: 2026-09-13T10:11:30.933Z
---

Do not push branches or open pull requests. Prepare the commit locally (worktree, staged files, drafted message and PR body) and hand over; the user runs `git push` and creates the PR.

**Why:** the user said "dont push the branch yourself" while I was consolidating the upstream PR (2026-09-13). Pushing is outward-facing and theirs to time and review. (Earlier in the campaign, pushes of the working branch `nle-stock` to their own fork were done routinely and accepted; the rule is for new branches/PR material — when in doubt, don't push.)

**How to apply:** stop at the local commit. Report the branch, the commit hash, the compare URL they would open, and where the drafted PR body lives. Same for the engine repo: the fast-nle main fast-forward is theirs to run. Related: [[no-claude-commit-attribution]].
