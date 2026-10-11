# NetHack ablation and cleanup audit

Audited 29 September 2026 against PufferLib `3719caaa`, with the current uncommitted champion `depth.ini`, and fast-nle `e7f656856`. This is an inventory and proposed experiment plan, not a record of new ablation results. No training or source changes were made for this audit.

## Individual mask campaign (complete)

Subsequently launched at the user's request: 35 interleaved 1B runs, five seeds each for baseline, no handless mask, zero-time masking on, no hostile-ray restriction, no strategic item restrictions, RUN/SEARCH20 disabled, and no verb epsilon. The architecture remains fixed. The strategic item gates and RUN/SEARCH20 are grouped variants.

Campaign directory: `/puffertank/experiments/nethack-mask-ablations-20260929/`. See its `README.md`, `manifest.json`, `VALIDATED.json`, and updating `RESULTS.md`. Detached tmux session: `nethack-mask-ablations`. Status: `python3 /puffertank/experiments/nethack-mask-ablations-20260929/status.py`.

## Combined-removal follow-up (2 October)

The individual campaign finished all 27 retained jobs with no failures; the remaining eight no-epsilon / no-RUN-SEARCH20 jobs were cancelled. Five seeds each of handless, hostile-ray and strategic item restriction removal preserved pooled score near baseline.

Now running five fresh 1B policies with **all three removals together**, using paired seeds 2901–2905 and the exact same binary, engine, architecture and hyperparameters. RUN/SEARCH20 and verb epsilon remain enabled; zero-time masking stays off. Each final checkpoint gets the same 6,000-game fork evaluation with the first 4,000 discarded. A combined-flags 2M-step training and real evaluation smoke check passed before launch.

Campaign: `/puffertank/experiments/nethack-mask-combined-20261002/`. Detached tmux session: `nethack-mask-combined`. Status: `python3 /puffertank/experiments/nethack-mask-combined-20261002/status.py`. Five completed matched baseline runs are referenced in `baseline_reference.json`. Failed training attempts receive fresh replacement seeds automatically, up to two retries.

### 2 October, 11:09 UTC update

Combined seed 2901 exited with SIGSEGV (`returncode=-11`) after its last logged 295.7M steps. The existing queue automatically scheduled fresh replacement seed 10135 and advanced to seed 2902. No trainer, engine, or config changes were made to this campaign. A small isolated Breakout reuse pilot was sharing the GPU during this interval; the cause of the NetHack crash is unresolved. No core dump was available (core size limit zero, host apport path absent inside the container). The failed attempt and partial checkpoints remain preserved in the campaign directory.

## Nearby-entity passthrough follow-up (queued 2 October)

At the user's request, five more 1B runs are queued with nearest-monster, nearest-floor-item and underfoot-item passthroughs removed together. Inventory passthroughs and the original baseline masks remain enabled. The 48 affected concat values are zeroed and their direct gradient contributions disabled; dimensions, parameter count and all other paths stay fixed. Planned seeds 2901–2905 match the existing baseline runs.

Campaign: `/puffertank/experiments/nethack-nearby-pass-20261002/`. Detached scheduler: `nethack-nearby-pass`. It waits for the current combined-mask batch's completion artifact, five successful evaluations, release of its queue lock and an idle GPU. The isolated control and ablation binaries are built; forward/backward fixtures, baseline trajectory comparison and training/evaluation smoke checks are scheduled before the five runs. GPU checks have not run while the current batch is active. Validation failure stops the new campaign.

Same evaluation protocol: 6,000 fork games per policy, discard 4,000 and retain 2,000. Failed training runs receive fresh replacement seeds. See the new campaign's `README.md`, `manifest.json`, `SCHEDULER_STATUS.json`, and `status.py`. The production source and current campaign are unchanged.

## What actually landed for the release

The final `78f446fe` (`nethack challenge`) patch changed only four files: handless-form and zero-time refusal masks, the public hunger gate for casting, stock-compatible autopickup options, and the score hyperparameters. Most architecture and action automation were already present in the earlier September release. The squashed history does not establish when every individual feature was introduced.

Current production code still has 12 item pointer heads; the later identify-target head is parked in the stash named `nethack work before reviewing cublas`. Discovery replacement is already available as `NH_DISC_SWAP=1`, but is off by default. Neither should silently enter the baseline.

## Masks and exploration

Source: `ocean/nethack/nethack.h:222` through `nethack_compute_mask`, and `nethack_policy.cu`.

| Feature | Current behaviour | Ablation or cleanup |
|---|---|---|
| Handless-form belief | Messages set `cant_hold`, blocking wield/throw/wear and Elbereth; transformation messages or a 100-world-turn expiry clear it. | On/off first. If useful, revisit the belief and expiry independently. It is not currently a config option. |
| Zero-time refusal memory | Blocks repeated refused choices until position/depth/time change. `NH_ZT_MASK` defaults off in training, on in stock C and Python eval. | Make settings explicit in every run manifest. Compare off/off and on/on training/eval; also test existing checkpoints with both eval settings. Current memory tracking still runs when masking is off. |
| Ranged targeting | THROW/ZAP prefer directions with visible hostile targets within eight tiles; a peaceful blocks the ray. All directions return if no target ray exists. CAST shares the ZAP direction head. | Test independently from basic direction legality. This can exclude useful noncombat targets, so it is a strategic restriction. |
| Peaceful movement / run rules | MOVE avoids adjacent peaceful monsters; RUN avoids adjacent hostiles, with fallback directions when blocked. | Separate strategic avoidance from impossible moves such as diagonal doorway movement. |
| Inventory rules | Class/worn/curse/layering checks; blind reading blocked; APPLY containers disabled because the macro cannot handle their menus. | Keep class/slot validity and explicitly document unsupported interactions. Removing container masks needs working container actions first. |
| Strategic item restrictions | No eating while satiated; no rereading a known book above 2,000 retention; no unaffordable shop pickup. | Test separately. These are not all equivalent to actions the game refuses. |
| RUN and SEARCH20 | Enabled in score config, both masked in current depth config. | Compare within one reward/config recipe. Do not attribute score-vs-depth differences to this alone. |
| Verb epsilon | Uniform legal-verb mixture starts at 0.005; anneals after 40% of training to zero at the end. | Set `verb_eps=0` for a clean existing-config ablation. Sampling and PPO likelihood must describe the same mixture. |

Keep consumed-head masking of PPO log-probability and entropy: only the chosen verb's arguments affect the executed action. That is distinct from hand-written strategic masks. Also retain nonempty dummy argument distributions for unused heads.

## Action automation

Source: `ocean/nethack/macros.h` and `nethack_execute` in `nethack.h`.

These are part of the policy interface, not just mask code:

- Pickaxe/mattock APPLY always digs **down**, overriding the chosen direction.
- WEAR automatically removes conflicting same-slot armour.
- Shop PICKUP automatically attempts payment; pile menus select all.
- ALTAR_ID drops eligible items with unknown blessed/uncursed/cursed status and picks them up again.
- ENGRAVE_ID automatically selects an unidentified wand not yet tested; testing memory is indexed by inventory letter.
- Skill enhancement automatically chooses the first available upgrade.
- Prompt handling chooses floor food, avoids cockatrice-family food, declines fountain drinking, and supplies default answers to many menus and confirmations.
- The current READ path uses generic menu handling, not the later learned identify-target head.

The downward-digging macro is especially relevant to interpreting depth-policy behaviour. Removing these helpers can change what the action space can express, so each needs a defined replacement rather than deleting prompt handling wholesale.

## Architecture candidates

The active CUDA forward is `ocean/nethack/nethack.cu:1952`; some surrounding comments describe older architectures.

| Component | Current behaviour | Useful comparison |
|---|---|---|
| Entity pooling | Inventory, monsters, floor items and spells have per-entity networks with sum and max pooling. Sum scaling is 0.2 for inventory and 0.25 for the other streams. Shared design, separate weights. | Max only, sum only, both; test fixed scaling separately from pooling type. |
| Inventory passthrough | Wielded and quivered item representations plus numerical state; worn-item mean; dedicated amulet/rings/eyewear panel. | Remove accessory panel alone, then the other passthrough groups. `NH_NOPASS` zeros all inventory passthrough; `NH_NO_APANEL` changes the layout. |
| Nearby-entity passthrough | Nearest monster, nearest floor item and underfoot-item summary go directly to concatenation alongside pooled streams. | Remove each group while retaining pooling. These paths are still active even though the article diagram omitted their labels. |
| Item bottleneck and discovery | Appearance, discovered identity and state are combined into a 16-dimensional ReLU representation. | Identity replacement (`NH_DISC_SWAP`), wider representation, signed/separate identity path. Keep width changes distinct from identity encoding changes. |
| Entity activation | Final per-entity layer uses ReLU before pooling. | Existing `NH_ENT_LINPOOL` tests a linear final layer. This does not remove the earlier 16-dimensional ReLU bottleneck. |
| Extra numerical features | Raw character features accompany the stats MLP; spell summaries and role/race/gender/alignment embeddings also enter concatenation. | Remove feature groups independently. Some character identity information is represented both in numerical features and learned embeddings. |
| Spatial representation | Semantic local crop MLP and a 592-feature global terrain/landmark representation. | Test feature groups before replacing the entire spatial encoder. The old global patch encoder is not the active path. |
| Message encoder | Default 1,024 hash buckets, 256-dimensional embeddings, normalized trigram sum. | Bucket/width changes or char CNN, with throughput and parameter count alongside learning results. |
| Pointer decoder | Per-verb item queries use query-only normalization and learned temperatures; key magnitudes still affect logits. | Fixed temperature, full cosine, or ordinary dot product as separate comparisons. Despite its name, `nh_ptr3_cos_kernel` does not currently normalize keys. |

Earlier frozen-policy and supervised discovery probes already motivate testing identity encoding and the bottleneck. Their readout results do not establish that a replacement improves RL behaviour. A wider bypass also changes capacity, so compare matched widths where possible.

The C demo has a separate implementation. Changes must either be mirrored there and checked or explicitly recorded as unsupported by that demo. Do not load old checkpoints into changed tensor layouts without checking compatibility.

## Cleanup without RL ablations

- Remove confirmed unused kernels and historical branches after checking all callers. There are multiple candidate leftovers from patch pooling, inventory pooling and old spell paths.
- Correct stale comments about encoder attention, auxiliary heads, tensor widths and cosine normalization.
- Consolidate observation/action layout definitions and duplicated head offsets without changing the serialized layout.
- Organize masks by purpose: argument validity, game refusal, macro limitations, and strategic preferences. Give experimental preferences explicit settings.
- Keep experiment manifests explicit about compile flags, environment variables, config, checkpoint and engine version.
- Preserve public-observation fixes, appearance-based weight, stock options and cast hunger visibility. These enforce the intended benchmark interface.

Use existing deterministic trajectories, observation comparisons and CPU/GPU or gradient checks appropriate to the edited code. A behaviour-preserving cleanup should reproduce the baseline before training any ablation.

## Suggested first experiments

1. Establish one current baseline and pin its source, config, flags and eval protocol.
2. Screen existing checkpoints for sensitivity to handless and zero-time masks, recording refused actions, world-turn progress and termination reasons. These are evaluation interventions, not substitutes for retraining.
3. Run isolated training variants: no handless mask; no verb epsilon; no accessory panel; no nearby-entity passthrough; no hostile-ray restriction. Use multiple paired seeds. A 1B screen is useful, but confirm promising removals at the eventual training budget.
4. Separately test identity replacement, pooling and representation width. Keep these architecture experiments apart from action-interface changes.
5. Evaluate score, depth/BALROG progression, actual landmark visits, item-use behaviour, no-progress failures and throughput. Keep reward coefficients fixed within comparisons and make train/eval mask differences explicit.

Do not combine all removals into one initial run: that would not tell us which additions help, harm, or compensate for each other.
