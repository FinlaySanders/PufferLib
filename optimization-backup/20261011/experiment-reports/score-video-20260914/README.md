# Score-policy descent clip

Policy: fixed 4B s705. Source: 512-agent vec eval, seed 73, environment 237, episode 3.
Final score 53,700; maximum dungeon depth 14. This is not an ascension or Castle run.
The vec replay reproduced the episode score, depth and 6,660-step length.
Standalone CPU action replay was NOT faithful and is not used here.

The clip uses saved C demo-renderer frames from steps 5,201–6,659, showing the late descent. Every second frame is shown at 12.5 fps (25 policy actions/second). The final reset frame is omitted to preserve the last live game screen. The playback footer replaces the original capture-rate label.

Source: /tmp/reg/vid/vecwatch_237_3.out
Episode log: /tmp/reg/vid/deep10k.ep
