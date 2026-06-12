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

## A/B result (vol-216, day 1): in-DFS growth is NET NEGATIVE at this scale

d146-seed63 finish config, 120 s × 4 seeds, gates clipped to each
frontier:

| et | finals | epochs/seed |
|---|---|---|
| 14 | 449, 449, **451, 451** | 12-24 |
| 18 | 448, 448, 448, 449 | 3-12 |
| 20 | 447, 448, 448, 449 | 3-15 |

Mechanism (config-specific result, but the mechanism generalizes):
per arrival, exact-20 weakly dominates walk+exact-14 IN THEORY. In
practice (a) **cap-hit**: the k=20 B&B exceeds the 100M node cap on
hard instances and degrades to greedy exactly where optimality
matters (the loud warn fired — the TAIL_CAP discipline works);
(b) each et20 call costs orders of magnitude more than et14,
collapsing epoch diversity (3-15 vs 12-24 epochs/seed) — the walk's
176→182 segment wasn't waste, it was cheap retry diversity.
Conclusion: value-LB + root-Hungarian is NOT yet strong enough to
make k≥18 pay in-DFS. Needs the next bound rung, or use big exact
regions post-hoc only (tail2polish at giant cap on record boards —
a 2-row rigidity probe extending the vol-207 exactness program).

## What's open

- Next bound rung: in-descent Hungarian on reduced costs at shallow
  B&B levels (root-only now); only then retry k≥18 in-DFS.
- Post-hoc 2-row exact polish of the 452 board (exact_tail2 needs the
  vol-216 bound upgrades first).
- LP-with-edge-terms as the next bound rung
  ([[assignment-lp-prefix-scoring]] has the machinery; ~ms via IPM is
  still too slow per et call — needs a cheap surrogate or caching).
- exact_tail2 (two-row column-pair B&B) same treatment.
- MIDDEN-confined exact regions (break_cells already plumbed).

## Linked

[[assignment-lp-prefix-scoring]], [[replay-prior-over-cost]],
[[midden-damage-geometry]], session [[vol-216]]
