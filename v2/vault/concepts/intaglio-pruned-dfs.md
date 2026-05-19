# INTAGLIO-pruned DFS

**Status**: `unbuilt` (Vol-147, planned 2026-05-19)

## Idea

Deterministic backtracking DFS over (cell, piece, rotation) with a
post-placement check that rejects any partial board containing a
forbidden 2×2 patch.

## Definition

After placing piece $p$ with rotation $r$ at cell position $c$, for
every 2×2 patch fully inside the partial board that contains $c$
(at most 4 patches), check the patch against a precomputed forbidden
table. If forbidden under all 4 rotational orientations of the patch,
prune the subtree.

The forbidden-2×2 table is a function:
$$f : (p_1, r_1, p_2, r_2, p_3, r_3, p_4, r_4) \to \{0, 1\}$$
where 1 means **forbidden**. This is too large to store densely
(1024⁴ entries) — must be:
- (a) computed on-the-fly from edge-color matching, OR
- (b) keyed only on the relevant boundary colors (8 colors per patch
  = 23⁸ = 78B → still too large), OR
- (c) keyed on the *piece set induced by the patch* (much smaller).

The right encoding is option (c): the patch is forbidden iff **no
rotation assignment to its 4 pieces makes all 4 internal edges match**.
This is checkable in O(4⁴=256) by enumeration; the forbidden table can
then memoize (sorted_piece_id_tuple) → bool. The table is keyed on
$\binom{256}{4} \approx 175M$ entries — too large; defer to on-the-fly.

## Why this is the right pruner

V138-V142 measured forbidden 2×2 rates:
- 99.72% of random 2×2 patches are forbidden under any rotation.
- Real boards: LOW score (<440) median 109 forbidden patches/board.
  HIGH (≥460): median 29 patches. The 463 record: 26 forbidden patches.
- A perfect 480 board has 0 forbidden patches.

If DFS allows any forbidden 2×2 to be placed, it commits to a subtree
that **cannot** reach 480. Pruning at first forbidden-2×2 violation
collapses the search space dramatically — IF the check is cheap enough.

## What we measure

- **nodes/sec with vs without patch-check** — overhead factor.
- **subtree pruning fraction** — how often does the check reject.
- **max-matched at fixed wallclock** vs `vanilla_fast` baseline.

## Open questions

1. Is the patch-check fast enough? On-the-fly is 4×4×4×4=256 ops per
   check; with bit-tricks, ~10ns. Per-node cost is ~4 checks ⇒ ~40ns
   added per node. vanilla_fast is ~85M nps single-thread → 11.7ns/node.
   This is **~4× slowdown** — borderline.

2. Does the check prune enough to overcome the slowdown? If 50% of
   subtrees are pruned at the patch level, that's a 2× nodes-saved.
   Net: 4× × 0.5 = 2× slowdown. Need pruning rate > 75% to break even.

3. **Combine with 2×3 patches?** V142: 100% of random 2×3 patches
   forbidden. 2×3 patches contain 6 pieces — more discriminatory but
   the patch-check is more expensive (6×4=24 ops vs 4×4=16). Defer to
   V147-followup.

## Linked

- [[forbidden-patch-theorem-2026-05-19]]
- [[../sessions/vol-147]]
- [[../plans/MULTI_VOL_PLAN_2026-05-19]]
