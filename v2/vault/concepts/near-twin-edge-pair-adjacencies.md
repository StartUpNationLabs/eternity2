---
name: near-twin-edge-pair-adjacencies
description: Across 421 high-score boards, top-19 piece-pair adjacencies are EDGE-EDGE pairs (1 border each); only 1 interior pair in top-20. Most common pair is V 26-27 (49.4%) — near-twin edges differing in one color.
metadata:
  type: project
status: built
---

# Near-twin edge-pair adjacencies (vol-99 finding)

**Status**: `built` — measured 2026-05-16 ~05:58.

## Method

For 421 complete high-score boards (score ≥ 455), aggregated all
piece-pair adjacencies (horizontal and vertical). Counted how
often each unordered pair appears adjacent.

## Top 10 universal piece pairs

| pair | direction | freq | piece types |
|---|---|---:|---|
| (26, 27) | V | 49.4% | both edge pieces (1 border each) |
| (4, 6)   | H | 46.3% | both edge |
| (10, 23) | H | 44.2% | both edge |
| (21, 226)| V | 42.3% | edge × interior |
| (18, 19) | H | 40.6% | both edge |
| (10, 21) | H | 40.4% | both edge |
| (69, 207)| H | 39.2% | both edge |
| (6, 14)  | H | 39.0% | both edge |
| (5, 21)  | H | 39.0% | both edge |
| (19, 25) | H | 39.0% | both edge |

**19 of top-20 pairs are EDGE-EDGE adjacencies.** Only 1 includes
an interior piece (226 with edge 21).

## Why?

Edge pieces have limited placement options — they MUST sit on the
60-position border ring of the 16×16 board, with their BORDER side
facing outward. Given the constrained color-matching on the
exterior ring, many high-score basins re-use the SAME edge-piece
arrangements.

The top pair (26, 27) — both have profile (0, BORDER, X, BORDER)
where their non-border colors differ by ONE color (6 vs 7). These
are NEAR-TWINS in the edge-piece subset, and they can interchange
or sit adjacent in many border configurations.

## Implication

The border-ring structure is significantly more constrained than
the interior. Even though basins disagree on corner permutation
(24 possible), they tend to agree on edge-piece pair adjacencies
within a perm-class.

This suggests **the border ring acts as a "modular constructor"**:
once corner perm is fixed, the border pieces follow a relatively
short list of arrangements, then the interior is filled.

A future record-attempt could exploit this: ENUMERATE all border-
ring arrangements per corner-perm class (small enumeration ~100k),
then use each as a seed for ALNS interior-fill. This decomposes
the search efficiently.

## Caveats

- 421 boards is a smaller corpus than the 1964 used for mismatch
  heatmap (full-board completion required).
- Top pairs are ~40-49% — strong correlation but not universal.
- No pair achieves 100% (consistent with corner-perm divergence).

## Linked

- [[universal-match-backbone]]
- [[universal-mismatch-heatmap]]
- [[basin-corner-permutations]]
- Memory: `project_e2_piece_set_symmetries.md` (near-twin pieces)
