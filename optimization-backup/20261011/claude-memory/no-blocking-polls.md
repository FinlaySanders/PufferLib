---
name: no-blocking-polls
description: Never block the chat with long sleep/poll loops in tool calls; run work in the background and check status with quick reads
metadata:
  type: feedback
---

Do not run tool calls that sleep or poll for minutes waiting on background jobs. Launch long work detached (nohup/setsid) and check it with instant reads when the user asks or between short steps.

**Why:** the user interrupted twice (2026-09-10) because multi-minute polling loops blocked the conversation; they want to be able to ask about progress at any time.
**How to apply:** background jobs write their own logs; status checks are single fast commands (tail/wc/ssh one-liners, no sleep); report what is running and its ETA instead of waiting for it. Related: [[nethack-stock-nle-bridge]].
