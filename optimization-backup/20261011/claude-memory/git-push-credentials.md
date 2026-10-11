---
name: git-push-credentials
description: "git push fails inside tmux on this box (stale VS Code askpass socket + Mac-path gh helper); push from a fresh VS Code terminal, or set up SSH remote / container gh"
metadata: 
  node_type: memory
  type: reference
  originSessionId: b5a6399e-3c2b-4b96-af84-b52fb0424b97
---

`git push` (HTTPS) fails in tmux panes on puffertank: the credential chain is
(1) a `/opt/homebrew/bin/gh` helper synced from the user's Mac gitconfig by
VS Code Dev Containers — path doesn't exist on Linux, gh not installed in the
container; (2) VS Code askpass via GIT_ASKPASS → `/run/user/1000/vscode-git-*.sock`,
which tmux freezes from a dead VS Code window (socket hash changes per attach).

**How to apply:** the user pushes from a fresh VS Code integrated terminal
(works — live askpass socket). Durable fixes offered but not yet adopted
(2026-07-10): SSH remote (`git remote set-url fork git@github.com:...`) or
in-container `gh auth login` + credential.helper. Remote `fork` =
github.com/FinlaySanders/PufferLib. Never attempt pushes from Claude's shell
without checking auth works first.
