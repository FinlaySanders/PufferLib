# Message encoder supervised comparison

Run: `/puffertank/experiments/message-supervised-20260914`.
Frozen executable source, source checksum, split membership, protocol, per-fit metrics and weights are stored there. `DONE` is written only after all 36 selected fits complete; `run.log` tracks progress.

- Trigram bags: 256 / 1,024 / 4,096 hash buckets crossed with 32 / 128 / 256 embedding dimensions.
- Character CNN: 16D byte embeddings, two width-5 convolutions (64 channels then output width), ReLU and masked global max; 32 / 128 / 256 output dimensions.
- Three initialization seeds; both learning rates 0.0003 and 0.001 tried for each. Same training split, supervised heads, epoch limit, validation selection and early stopping.
- Up to 80 epochs; batch 256; Adam; validation plateau learning-rate reduction. Test evaluated only on the selected checkpoint and learning rate.
- All encoder weights train jointly with linear event and species readouts. This is supervised capacity testing, not a frozen RL probe or an RL comparison.

The historical corpus `/tmp/msg_s701.bin` has 60,000 frames, each containing 1,046 float32 encoder values plus 128 message bytes. Only the raw text is used. Its 7,221 distinct nonempty lowercased messages are split 80/10/10 with seed 1409; each distinct message is weighted equally. Exact messages cannot cross splits. Episode identifiers are unavailable, so these are **held-out message strings, not held-out games**, and related templates may cross splits.

Targets are 12 regex-derived event indicators (per-task AUROC), plus killed/attacking monster species where the training split supports at least ten distinct messages per class (accuracy and majority baseline). Species class selection uses only training data. Full patterns and split coverage are in `protocol.json`. Rare-label scores require caution; these tasks measure recoverability of textual cues, not general language understanding.

The trigram encoder uses the production lowercase/hash/normalized-sum computation. Vocabulary size means hash bucket count, not a separate vocabulary setting. The sweep also varies vector width. CNNs receive the same lowercased bytes. Architectures share output widths and optimization budgets but are not parameter-matched. Parameter counts and fit times are recorded; training time is not an inference-speed benchmark.

## Frozen random encoder comparison

`run_frozen.py` repeats the full 12-architecture, three-seed grid with randomly initialized encoder weights frozen. Only the linear event/species heads are fitted. Encoder parameters are checked for exact equality before/after every fit. Outputs are cached; feature normalization uses training statistics only, and constant training coordinates are zeroed on all splits. Heads start at zero. Probe learning rates 0.001 / 0.003 / 0.01 and up to 200 epochs are selected on validation loss, with early stopping after at least 60 epochs and 25 epochs without improvement. This gives linear readouts their own convergence budget; the supervised-encoder comparison used two learning rates and 80 epochs.

Frozen source and results: `/puffertank/experiments/message-frozen-20260914`. Summary: `FROZEN_RESULTS.md` and `frozen_results.json`. Data, split membership, target definitions and architecture initializations match the supervised grid. This tests information accessible through a trained linear readout of an untrained representation. It does **not** test an entirely untrained system or show that an RL policy can dispense with training.
