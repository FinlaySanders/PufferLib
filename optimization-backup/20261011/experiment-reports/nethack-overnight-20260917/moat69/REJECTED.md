# Rejected: terrain view is transiently stale during level generation

{
  "time": "2026-09-18T03:04:10.652120+00:00",
  "candidate": "moat69",
  "decision": "REJECTED behavior divergence; restored hack.h,68provisional remains",
  "correctness": "scoreprefix passed,depthfailed env90 event44876/F/T2529;diagnostic gdb caught moat cache mismatch43,8 during maketrap->mktrap->speciallevelgeneration->mklev",
  "lesson": "Compact terrain plane not synchronized throughout level generation; is_moat must retain raw read. Do not broaden existing fastview assumptions or weaken oracle."
}

Diagnostic backtrace: ../moat69-diag/gdb.log. No baseline/game behavior fix was made.
