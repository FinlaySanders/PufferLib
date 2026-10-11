# Hot object prefix experiment

The retained trace's largest private category is hero inventory(4.28KiB per
decision), followed by floor objects(3.79KiB). inv_weight, inventory export,
and floor-object selection repeatedly read next pointer, quantity, weight,
type, position and class. Move those plus enchantment, inventory letter,
artifact index and worn mask into the first32bytes. Keep the88byte object,
all field types and the96byte save representation. Full named-field legacy
conversion replaces the old offset-specific memcpy helper.

objhead32 changes field placement only, using the retained88byte-slot pool.
objhead32_slots also uses96byte slots aligned to32bytes in64byte-aligned
blocks, so every32byte hot prefix is physically contained in one line.
The object record remains88bytes;8byte slot padding increases pool memory by
about9%. This is distinct from the earlier objhot change, which only moved
the container pointer and left common fields spread over the first50bytes.

Validate all saved fields, allocation/reuse/isolation/teardown, and the
golden/fuzz/interleaved gates before timing. No retention without repeated
native improvements and complete score/depth decision comparisons.
