# Monster field-access diagnostic

Existing instrumented compact_pool engine, identical120-byte monster layout
to retained rawglyph, new runtime override only.512 games after8192 warm
recorded actions,4 measured decisions each. End-state hash e19798d5fd4e1c2e
and14191 turn advances match the independently saved reference. Counter
boundary/copy test passes. No instrumented timing used as native performance.

2048 decisions,55052 registered monster-record steps,53119 touched. Scalar
movement/HP/data/cham are accessed in94–99% of touched records. Worn-mask and
strategy in63%/61%, eating55%, inventory54%, weapon47%, tracking46%. Pointer
to extra role data2.1%, identity1.1%. mlstmv0.11%: the earlier audit mistakenly
classified the guarded special-case parked-guard branch as general movement.

Important coverage limitation: clang's existing trace-loads instrumentation
misses bitfield accesses here. movemon_disassembly.txt shows loads at offsets
60,64,66 without callbacks. Therefore status bits are explicitly forced hot;
raw byte/line totals are incomplete lower bounds, not a complete footprint.
Do not use the very low recorded status-bit rate as evidence of coldness.
This also limits older line-only diagnostics; they remain source-access
comparisons, not hardware cache-miss measurements.

The evidence motivates monmove_line: replace the prior first-line extra-data
pointer with common strategy/worn/eating checks, while keeping flags hot and
putting inventory/track fields on the second line. Test this simple aligned
layout before implementing a separate cold allocation and deep-copy plumbing.

Potential diagnostic repair for future layout work: installed clang advertises
-ffine-grained-bitfield-accesses, which requests legal-width accesses instead
of large integer runs. A tiny bitfield_probe.c is prepared to inspect whether
this restores sanitizer callbacks without changing struct layout. Not compiled
or tested yet; do not claim the coverage problem fixed. No broad recapture is
needed for the current timing decision because status flags were kept hot.

The tiny bitfield probe has now been compiled with the generated include path.
Default Clang O3 produces one i56 load and no sanitizer load callback for the
three requested flags. -ffine-grained-bitfield-accesses produces two i8 loads,
both with __sanitizer_cov_load1 callbacks. Exact LLVM IR and commands are in
bitfield_probe_with_generated_result.json / bitfield_*_with_generated.ll. This
repairs coverage in this small probe only; the full engine trace has NOT been
rebuilt or recaptured. Existing incomplete trace conclusions remain qualified.
Instrumented accesses still are not hardware cache misses; code generation
changes also alter the spans loaded. Initial missing-pm.h compile attempts are
archived separately rather than overwritten.
