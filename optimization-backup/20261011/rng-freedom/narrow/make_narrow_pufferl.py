# Trainer-side half of the grid narrowing (cast obs/mask, zero_term_state, record_step): bodies -> grid-stride loops with
# element-local returns as continue; launches inside the rollout forward capped via nh_narrow_grid(..., false). See the inline
# session transcript for the exact transformation; narrowing.patch holds the result against the pre-narrowing source.
