---
name: pufferbox3-container-paths
description: This shell is a Docker container on pufferbox3; /puffertank/pufferlib is container-only, and the user's scp login (puffer@pufferbox3) sees only /puffertank/docker as ~/puffertank
metadata:
  type: project
---

The Claude shell runs inside a Docker container on pufferbox3 (/.dockerenv, containerd overlay). `/puffertank/pufferlib`
and the rest of `/puffertank` are in the container's overlay filesystem and DO NOT exist on the host. The only
host-mounted directory is `/puffertank/docker` (ext4, owned by ubuntu), which the user's `puffer@pufferbox3` login sees
as `~/puffertank` (their `scp -r puffer@pufferbox3:puffertank/nethack_4B_logs .` works; `nethack_4B_logs` is in there).

**Why:** 2026-09-13 the user's `scp puffer@pufferbox3:puffertank/pufferlib/...` failed "No such file or directory"; the
repo path is invisible from the host.

**How to apply:** to hand files to the user, copy them into `/puffertank/docker/<name>/` and give
`scp -r puffer@pufferbox3:puffertank/<name> .`. Article figures staged at /puffertank/docker/nethack_article/.
Related: [[nethack-article-figures]].
