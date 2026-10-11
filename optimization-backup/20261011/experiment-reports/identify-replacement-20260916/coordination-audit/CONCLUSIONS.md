# Conclusions

The decoder is correctly conditioned on the verb: one item query per item-using verb, with PPO's consumed-head map selecting the chosen verb and its arguments. Parallel evaluation does not invert the factorization P(v,i|s)=P(v|s)P(i|s,v). The verb head has no direct access to the item logits; it receives inventory information through the shared encoder/recurrent path.

Completed 48,000 real rollout decisions across two policies and three trajectory seeds each. Obtained 376 paired armour contexts from seven episodes for additive and 309 from six episodes for replacement. These are correlated diagnostic samples, not independent cert episodes.

In contexts with more than one eligible armour item, changing a candidate from a known downgrade to known upgrade increases conditional candidate probability from 11.21% to 97.59% (additive,331 contexts) and 47.14% to 99.13% (replacement,234 contexts). Across all paired contexts, mean WEAR probability is 0.6712% to 0.6761% and 0.8947% to 0.9034%, respectively.

The small absolute movement does not mean absent information: replacement WEAR odds increase in 84.47% of states, with median paired log-odds change 1.649 (about 5.2x odds). In the quiet subset, odds increase in 97.26% of 73 contexts, with median log-odds change 2.614. WEAR is often extremely unlikely in both variants. Additive median paired log-odds change is 0.136 (about 1.15x odds).

Pool-swap assertions pass for all 685 cases: verb logits follow the donated pool exactly while the candidate vectors remain from the opposite variant. This confirms the information route. Unknown enchantment or BUC does not rescue WEAR; resetting recurrent history does not produce a broadly strong response either. Same-slot armour replacement is handled automatically by the environment, ruling out a requirement to select TAKEOFF first.

Interpretation: clear item ranking, much weaker absolute willingness to act in these sampled states, with a demonstrable upgrade signal reaching the replacement policy's verb head. This is a learned action-selection limitation candidate, not evidence of reversed conditioning, total pooling blindness, or a proven hard 16D capacity bottleneck. The separate supervised capacity study found 96.57% AC-upgrade balanced accuracy for the baseline topology, with no material gain from widening or removing the first ReLU.

Remaining causal uncertainty: hypothetical observations were changed for a single decision with original history/messages/auxiliary stats and masks retained. A coherent game-state intervention followed over multiple decisions is needed before concluding the policy persistently ignores a real available upgrade. No decoder redesign or RL training was performed.
