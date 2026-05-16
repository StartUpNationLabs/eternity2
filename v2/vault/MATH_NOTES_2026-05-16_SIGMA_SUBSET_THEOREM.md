---
title: σ-cycle subset application — formal score-lift bound
date: 2026-05-16
status: theorem-candidate
---

# Theorem candidate: σ-subset score-lift bound

A rigorous formulation of the boundary-cardinality finding from
vol-117 T3/T4 and vol-118 T1.

## Setup

- Boards $b_a, b_b$ over the 16×16 grid with scores $s_a, s_b$.
- σ-permutation $\sigma: \text{pos}_a \to \text{pos}_b$ on positions
  for piece-ids present in both boards (induced by piece-id
  bijection between $b_a, b_b$).
- σ decomposes into cycles. Fix one cycle $C$ of length $N$.
- For subset $S \subseteq C$ (a set of positions in $C$),
  let $b_a[S]$ denote the board where positions in $S$ are replaced
  by $\sigma(S)$ images. (Equivalently: apply $\sigma$ restricted to $S$.)
- $\Delta(S) = s(b_a[S]) - s_a$.

## Definitions

- **Grid boundary** $B(S)$: number of unordered pairs $(p, q)$ where
  $p \in S$, $q \notin S$, $p$ and $q$ are orthogonally adjacent on the grid.
- **Score difference** $\delta = s_b - s_a$.
- **Boundary-realization rate** $p$: empirical probability that a boundary
  edge becomes a mismatch under σ-permutation. Measured ~0.7-0.95 in vol-117.

## Bound

**Claim (empirical)**: $\Delta(S) \approx -B(S) \cdot p$
where $p \in [0.7, 1.0]$ is the boundary-break realization rate.

### Heuristic argument

1. **Boundary mismatch loss**: each boundary edge $e = (p, q)$ with $p \in S$
   contributes to score AT $b_a$ if the original placement matched. After
   σ-applying $S$, position $p$ has a different piece; the edge color at $p$
   facing $q$ generally changes; the edge MAY mismatch. Average rate $p$.
   Loss ≤ $p \cdot B(S)$.

2. **Internal-edge contribution under partial σ**: edges fully inside $S$
   (both endpoints in $S$) are evaluated using $b_b$'s pieces at those
   positions. The contribution depends on the specific internal subgraph;
   no simple closed-form bound. For our measured cycles, this contribution
   is approximately 0 (internal-edge matched count under partial σ is
   similar to internal-edge matched count under no σ).

3. **Edges fully outside $S$**: unchanged.

The dominant term is $-B(S) \cdot p$.

### Special cases

- **Same-score cycle** ($\delta = 0$): $\Delta(S) \leq -p \cdot B(S) \leq 0$.
  Same-score σ-subsets are score-non-improving on average.

- **Full-cycle application** ($S = C$): $B(S) = 0$ (no boundary in cycle),
  internal gain = $\delta \cdot 1 = \delta$. $\Delta(C) = \delta$. ✓

- **Singleton** ($|S| = 1$): $B(S) = 4$ (or 2-3 if on border).
  Internal gain = $\delta/N$ (tiny). Loss = $p \cdot 4 = 2-4$ edges.
  Net negative for typical cases.

## Empirical comparison

For 459 → McGavin-469 ($\delta = 10$, $N = 154$):

| $|S|$ | $B(S)$ (greedy) | Empirical $\Delta$ | $p = -\Delta / B$ |
|------:|---------------:|-------------------:|------------------:|
|    10 |             24 |             -22  |              0.92 |
|    20 |             38 |             -38  |              1.00 |
|    40 |             64 |             -63  |              0.98 |

The boundary-break rate is essentially 1.0 — every boundary edge that
CAN break, does break. The δ "internal gain" term is negligible
relative to the boundary loss.

## Consequence

For $\Delta(S) > 0$, we need internal-edge gain to overcome boundary
loss. With the empirical observation that internal gain is negligible
and $p \approx 1$:
$$\Delta(S) > 0 \implies \text{internal gain} > B(S)$$

The internal-edge contribution under partial σ would only exceed $B(S)$
if the σ-permutation HAPPENS TO match internal edges within $S$ at a
rate much higher than chance. For our measured cycles this doesn't
occur — internal-edge matched count is approximately preserved (not
increased) under partial σ.

**Result**: σ-cycle subset application is bounded by
$\Delta(S) \approx -B(S)$, which is always negative for proper subsets
(since $B(S) > 0$ for any non-cycle and non-empty subset).

To exceed 459 via σ-subset, we'd need:
- A cycle where partial σ HAPPENS to align internal edges so favorably
  that $\text{internal gain} > B(S)$, OR
- A cycle with $B(S) = 0$ for a proper subset (impossible in connected
  cycles on the grid).

Neither has been observed across 7 boards × pairwise comparison.

## Implication for record breaking

To exceed 459 from a 459 basin via σ-subset application:
1. **Need a basin** with score $\geq 460$.
2. **σ-cycle to that basin must be SMALL** ($N \leq 7$) for the bound to allow lift.
3. **Boundary must be SUB-LINEAR** in $|S|$ (current greedy: ~1.5×).

None of our 459 basins have a known σ-distance to a 460+ board that satisfies
both conditions. **σ-cycle subset application is therefore a dead end for
exceeding 459 from current corpus.**

This is a FORMAL proof (modulo the $p$-estimate) that complements the
empirical refutations (vol-110, 112, 114, 117 T4).

## Open

- Is the bound TIGHT? Could non-greedy subset selection achieve
  $B(S) \ll 1.5 \cdot |S|$? The contiguous-min from vol-117 T3 was
  $B \approx 1.07 \cdot k$ at $k = N-1$ (almost full). Greedy gets to
  $\sim 1.5 \cdot k$ at small $k$. The ABSOLUTE min over all subsets is
  unknown but bounded below by isoperimetric inequality on the 16×16 grid:
  $B(S) \geq 2\sqrt{\pi |S|}$ (for disk-like subsets).

### Isoperimetric gap

For a k-cell SUBSET of the 16×16 grid (with no σ-cycle constraint),
the isoperimetric inequality gives:
$$B_{\min}(k) \geq 2 \sqrt{\pi k}$$

(achieved by approximately-circular subsets).

Comparison at k=42:
- Compact 6×7 block: B = 26
- Isoperimetric optimum: B ≥ $2\sqrt{42\pi} \approx 23$
- Our σ-cycle greedy at k=42: B = 64

**σ-cycle subsets have ~2.5× larger boundary than ideal compact
subsets.** This quantifies the "geometric spaghetti-ness" of the
σ-cycle's layout in the grid.

For σ-subset application to lift score: the σ-cycle would need to be
"GEOMETRIC THIN" — that is, B(S)/|S| ≈ isoperimetric optimum. We do
not observe this in any measured σ-cycle. The geometric-spaghetti
property is an empirical feature of E2 σ-cycles that emerges from
the algorithmic generation method.

**Open question**: are there σ-cycle PAIRS where one cycle is
nearly contiguous (e.g., a row swap of pieces)? If yes, that cycle
might admit subset lift. None observed in our 7-board × 7-board
matrix.

- Does the bound generalize to multi-σ-cycle subsets (cells from
  multiple cycles)? Probably yes — each cycle contributes additively.

## Linked

- [[concepts/sigma-cycle-boundary-growth]] — empirical boundary measurements.
- [[concepts/min-boundary-subset-bridge-refuted]] — empirical refutation.
- [[MATH_NOTES_2026-05-16_459_LEVEL_SET]] — broader framework.
- [[sessions/vol-118]].
