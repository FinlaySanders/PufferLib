# Experimental fusion dispatch correction

The experimental `NH_FUSED_BR` switch was intended to distinguish inference (1), training (2), and both (3). In the isolated encoder, `nethack_encoder_reg_train` assigned `training = true` immediately before zero-initializing the activation structure. This erased the flag.

Consequently, earlier mode-1 measurements enabled fusion in both inference and PPO. Earlier mode-2 measurements enabled it in neither. The recorded timings are real, but their descriptions as inference-only or training-only were incorrect. This affected no retained implementation or production source.

The initialization order is corrected in `TRAINING_FLAG_FIX.patch`, built as `dispatch_fixed_v20`. `BR_FIXED_PROOF_SUMMARY.json` confirms that mode 1 now leaves all five training-state files byte-identical to baseline after 113 real updates, including the first and last raw gradients. No training fusion plans were created.

Corrected measurements:

| Arm | Isolated throughput gain | Mature full-pipeline gain |
| --- | ---: | ---: |
| Inference-only fusion | 8.19% | 0.111% |
| Training-only fusion | 1.58% | 0.222% |

Full controls averaged 199,207 SPS with 0.026% drift. All 80 observation boundaries, frozen actor hashes and training work counts match. Neither arm meets the 1% end-to-end retention gate; both are parked individually.

Fusion changes rounding by adding bias before the intermediate BF16 rounding point. Inference output relative L2 difference is 0.00738 on the saved batch; values are finite. The earlier combined variant's first-gradient relative L2 difference of 0.134 came predominantly from unintentionally enabling training fusion. Its 1.03%/1.13% repeated throughput gain is evidence for that combined both-path variant, not for the intended inference-only combination. It has not been retained or established to preserve learning outcomes.

Source snapshots, component numerical comparisons and corrected timing records are preserved in `RANK_COMPONENT_PROOFS_SUMMARY.json`, `BR_FIXED_SCREEN_SUMMARY.json`, and `BR_FIXED_FULL_SUMMARY.json`.
