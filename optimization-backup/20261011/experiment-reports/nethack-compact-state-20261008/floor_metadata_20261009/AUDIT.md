# Floor movement metadata prototype

The existing per-game floor index holds object pointers and two coordinate arrays.
This prototype adds one packed 32-bit word per entry: type (10 bits), class
(6 bits), x (8 bits), y (8 bits). Compile-time bounds cover type/class enums;
coordinates round-trip through the original xchar type, including signed extrema.

The movement consumer uses that word for its initial rejection and interest
checks. It still accesses the full object for corpse properties, item utility,
artifact handling, carrying capacity and subsequent live coordinates. The order
of predicates, side-effecting calls, random draws and returned objects is unchanged.
searches_for_item was inspected: it is a read-only predicate and does not mutate
objects between the cached field reads.

The index is rebuilt only after invalidation, not on every game step. Existing
coordinate/list/restore invalidations remain. All 53 explicit pointer stores to
type/class now use setters that invalidate only for floor objects. The assignment
audit is in type_stores.json. Remaining dot-field assignments are temporary/dummy
objects. Construction and copying happen before insertion; floor splitting,
replacement and restoration already invalidate the index. A generation change
during traversal switches the cursor to the original live linked-list traversal.
Overflow beyond 2048 cached objects likewise uses the original traversal.

The extra index allocates 8 KiB per game. This deliberately duplicates a few fields
to reduce scattered record reads; it does not claim to shrink total allocation.
It tests the compact-hot-view hypothesis before attempting an authoritative
object-storage redesign. Type/class setters add a maintenance burden, which must
be justified by measured throughput.

Checks: independent linked-list reference, 974402 queries and 969602 matches,
identical hash d36de4e9538f4490, including automatic type/class invalidation,
mid-cursor mutations, changing bounds, signed extrema and 5000-item overflow.
Both reference and candidate pass Valgrind with zero errors and no leaks. Five
immutable golden/fuzz suites pass. Initial mature replay: 262144 decisions match
the pre-existing reference exactly. These are bounded checks, not a guarantee of
all possible game dynamics.

No production code, expected trajectories or retained source/library were edited.
