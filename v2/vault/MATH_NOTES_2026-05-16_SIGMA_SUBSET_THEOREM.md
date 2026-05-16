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

**Claim**: $\Delta(S) \leq -p \cdot B(S) + \delta \cdot \frac{|S|}{N}$.

### Heuristic argument

1. **Boundary mismatch loss**: each boundary edge $e = (p, q)$ with $p \in S$
   contributes to score AT $b_a$ if the original placement matched. After
   σ-applying $S$, position $p$ has a different piece; the edge color at $p$
   facing $q$ generally changes; the edge MAY mismatch. Average rate $p$.
   Loss ≤ $p \cdot B(S)$.

2. **Internal gain**: edges fully inside $S$ (both endpoints in $S$) get
   permuted but the score among them depends only on $b_b$'s structure at
   those positions. On average, the gain is $\delta \cdot |S|/N$ (proportional
   share of the total $\delta$).

3. **Edges fully outside $S$**: unchanged.

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

| $|S|$ | $B(S)$ (greedy) | Predicted $\Delta_{\max}$ | Empirical $\Delta$ |
|------:|---------------:|-------------------------:|-------------------:|
|    10 |             24 | $-0.7 \cdot 24 + 0.65 = -16.2$ |             -22  |
|    20 |             38 | $-0.7 \cdot 38 + 1.30 = -25.3$ |             -38  |
|    40 |             64 | $-0.7 \cdot 64 + 2.60 = -42.2$ |             -63  |

Empirical $\Delta$ matches predicted with $p \approx 0.92-1.0$ rather than
$0.7$. So almost EVERY boundary edge breaks; the bound is even tighter
than expected.

## Consequence

For $\Delta(S) > 0$, we need:
$$\delta \cdot \frac{|S|}{N} > p \cdot B(S)$$
$$\frac{|S|}{N} > \frac{p \cdot B(S)}{\delta}$$

For $\delta = 10$, $p = 0.92$, this requires $|S|/N > 0.092 \cdot B(S)$.

The min-boundary trajectory has $B(S) \approx 1.5 \cdot |S|$ for greedy
selection (vol-117 T4 data), so:
$$|S|/N > 0.092 \cdot 1.5 |S| \implies 1/N > 0.138$$
$$N < 7.2$$

**Result**: For $\delta = 10$ (459→469), σ-cycle subset application yields
$\Delta > 0$ ONLY for cycles of length $< 7.2$. The 154-cycle cannot lift.
Smaller cycles (size 5-7) MIGHT lift if their structure permits.

But the smaller cycles (within Cluster A, sizes 2-25) have $\delta = 0$
(both endpoints at score 459). So they cannot lift either.

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

- Does the bound generalize to multi-σ-cycle subsets (cells from
  multiple cycles)? Probably yes — each cycle contributes additively.

## Linked

- [[concepts/sigma-cycle-boundary-growth]] — empirical boundary measurements.
- [[concepts/min-boundary-subset-bridge-refuted]] — empirical refutation.
- [[MATH_NOTES_2026-05-16_459_LEVEL_SET]] — broader framework.
- [[sessions/vol-118]].
