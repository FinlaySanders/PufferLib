# Property representation audit

Candidate narrows only property source masks and timeout/flag words to int32_t. Defined source bits end at 0x00400000; intrinsic flags and the 24-bit timeout occupy bits below bit 30. Timer setters already clamp to TIMEOUT. Quantities, game turns, health, RNG state and score remain unchanged.

Updated every long-pointer helper in attrib.c and artifact.c, the set/incr_itimeout APIs and timeout.c intrinsic pointer. The build has no incompatible-pointer or changed-format diagnostics. Macros with long constants preserve the existing wider arithmetic where used.

Array alignment stays equal to the original long alignment so the unchanged prefix/suffix retain their layouts. Generated legacy hero struct retains the original save bytes and version fingerprint; explicit boundary conversion preserves saves. Compile-time assertions verify the prefix/suffix layout and a byte-for-byte in-memory save round-trip passes with all properties populated, including maximum defined flag/timeout values.

Measured allocation: prop 24->12 bytes, hero 2400->1584 bytes, main context176000->175184 bytes. Quick gates pass34 goldens26 fuzz, status disabled, interleaved and shuffled-thread games. Full saved-action hash comparison and native throughput remain required before retention. The save-layout declaration is deliberately explicit in this prototype; clean it up if the performance result warrants retaining it.
