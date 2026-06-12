---
name: exact-region-growth
description: "Vol-216 binding 3: grow the exact endgame from et14 toward et20-28 with stronger admissible bounds — value-based per-cell LB (vs the old 0/1 sat bound) + Hungarian assignment root cut in exact_tail; k>14 made safe (old fixed [_;56] candidate array would overflow). The only practical-complexity lever per the 480 perspective."
status: partial
metadata:
  type: concept
---

# Exact-region growth (et14 → et20+)

**Origin**: vol-216 binding 3, from the 480 perspective: records =
search × multipliers × **exact-region**; growing the proven-optimal
tail is the only lever that changes practical complexity rather than
constants. Each +1 cell of exact region removes ~one branching decade
from the lottery (~6 decades for et14→et20).

**Files**: `crates/cloister/src/endgame.rs` (`exact_tail`,
`hungarian_lb`), tests `exact_tail_k6_optimal_vs_brute_force`,
`exact_tail_k20_smoke`, `hungarian_lb_basic`.

## What shipped (vol-216, day 1)

1. **k > 14 support**: the candidate buffer was a fixed `[_; 56]`
   array (14 pieces × 4 rots) — silent UB-free but would panic/overflow
   for `--exact-tail 20`. Now per-level Vec scratch. et up to 64 cells
   is mechanically safe (u64 pool masks).
2. **Value-based admissible LB** replacing the 0/1 sat bound:
   per tail cell, static min-rot mismatch cost vs prefix-known
   constraints, sorted per-cell candidate lists; LB = Σ first-available
   cost (counts 2-constraint cells at their true cost, not 1).
3. **Hungarian root cut**: exact min-cost assignment (O(k³)) over the
   static cost matrix (forced cells pinned, reserved pieces excluded,
   MIDDEN perfect-only cells restricted to cost-0 entries). If the
   assignment relaxation already meets the cut, the entire B&B is
   skipped. Admissible because static costs ignore tail-internal edges.

Exactness preserved: brute-force equality tests at k=4 (legacy) and
k=6 (new), perfect-completion smoke at k=20.

## What's open

- Wall-clock A/B: et14 vs et18/et20/et24 on the d146-seed63 finish
  config — does the bigger exact region lift finals at equal budget?
  (Queued behind the ACTUARY calibration runs.)
- In-descent Hungarian at shallow B&B levels (root-only now).
- LP-with-edge-terms as the next bound rung
  ([[assignment-lp-prefix-scoring]] has the machinery; ~ms via IPM is
  still too slow per et call — needs a cheap surrogate or caching).
- exact_tail2 (two-row column-pair B&B) same treatment.
- MIDDEN-confined exact regions (break_cells already plumbed).

## Linked

[[assignment-lp-prefix-scoring]], [[replay-prior-over-cost]],
[[midden-damage-geometry]], session [[vol-216]]
