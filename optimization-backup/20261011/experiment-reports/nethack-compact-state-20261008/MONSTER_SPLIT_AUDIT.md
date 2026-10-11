# Next monster-state hypothesis (not implemented)

The current movement-first prototype keeps120-byte records in128-byte aligned
slots. Its CPU benefit repeats, but the frozen training pipeline is flat. The
pending paired fine-bitfield source trace will measure its footprint before a
more invasive split is attempted.

A concrete next layout could use64-byte hot records and separate64-byte cold
records in the same per-game allocation block. Hot payload is56bytes: list and
species pointers, HP/maxHP/special timeout, strategy/worn/eating, movement/cham,
coordinates/tameness and all status bits; the remaining8bytes hold the cold
pointer. Cold payload is64bytes: ID/type/level/alignment, track history,
appearance/type, weapon-check/extrinsics, trap/state flags, last-move time,
inventory/weapon/extra pointers. Exact compiled size/offset assertions are
required before any benchmark. Types and valid ranges remain unchanged.

The earlier scalar trace estimates cold data is needed by roughly57% of
active monster records under a56-byte-hot selection. This is a counterfactual
with incomplete bitfield coverage, not a measured miss rate or speedup. Packing
hot records consecutively may reduce adjacent-line pollution and page footprint;
following a cold pointer may cancel the gain. Decide from the repaired trace
and a short prototype, not from this estimate alone.

Ownership/copy sites that must be handled:
- makemon.c allocates/reset-clears with zeromonst and clones with whole-struct
  assignment. Cold storage must survive reset and copy values without aliasing.
- mkobj.c creates object-carried monster traits, memcpy-copies them, and assigns
  saved traits when reviving. These must copy cold values into destination-owned
  storage while preserving the existing separate mextra-copy semantics.
- restore.c calls newmonst then mon_from_legacy; its current memset must not
  discard the destination cold pointer. Keep144-byte legacy representation.
- youmonst is embedded per-context, not pool-allocated. Give it separate embedded
  cold storage and initialize its pointer during context fixup.
- makemon.c, mplayer.c and teleport.c use stack fakemon values. Each needs stack
  cold storage; do not allocate lazily or use a shared mutable zero record.
- teardown/reuse must free existing mextra ownership before returning a hot slot;
  whole pool blocks own both arrays. No per-monster cold malloc is necessary.

The audit only prepares a hypothesis; no source has been split and no benefit
is claimed. Require quick trajectories, copy/save/lifecycle tests, repeated
native gains, full immutable decision comparisons, freshPGO and frozen pipeline
checks before retaining any split.
