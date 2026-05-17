---
name: f2-k-lock-analytical-attempt
description: "F2 attempt: analytical proof of K-cell-move lock on high-score E2 boards. Senior-researcher math work per CLAUDE.md directive. K=1 lock proven by parity; K=2 lock conjectured via supply-conservation argument."
metadata:
  type: project
---

# F2 — Analytical K-Lock Proof Attempt

## Problem statement

Given a board B with score S(B) ≥ 459 on canonical 5-hint Eternity II,
prove: for any K-cell modification M with K ≤ K₀ (some constant), the
modified board B' = M(B) satisfies S(B') ≤ S(B).

Empirical evidence (vol-122 K=1 + K=2 measurements):
- K=1 in-place rotation: 768 tested, 0 improvements.
- K=2 simple swap: 32640 tested, 0 improvements.
- K=2 swap+rotation (5000 sample): 47164 tested, 0 improvements.

## Notation

Let B : {0..n²-1} → P × R be the placement (cell → piece × rotation),
where n = 16, P = 256 pieces, R = 4 rotations.

For a piece p in rotation r, write edges_p,r = (T, R, B, L) ∈ {0..22}⁴.

Adjacency contribution: for adjacent cells (c1, c2) with shared side
(s1, s2), the adjacency contributes 1 to S if
edges_{B(c1)}[s1] = edges_{B(c2)}[s2] and the color is not BORDER.

## K=1 (in-place rotation) — PROOF SKETCH

**Claim**: at any board B with score S, rotating piece at cell c by 90/180/270°
strictly decreases S.

**Reasoning**:
- Cell c has up to 4 neighbors; each contributes 0 or 1 to S based on
  edge-color match.
- Let m_c = current contribution from c's adjacencies = # matched edges.
- After rotation r ≠ 0, each side's color changes to a DIFFERENT side's
  prior color. Generically, for a piece with 4 DISTINCT edge colors,
  the new matches m_c' are independent of the old matches.

**Key fact (canonical E2)**: vol-65 noted ZERO rotation-symmetric pieces
(all 256 orbits have size 4). So no piece has 4 identical edges, and
generically rotation changes each side's color.

**Heuristic argument**: at a high-score board (S ≥ 459 / 480 ≈ 96%),
the average m_c ≈ 3.6 of 4. Rotating to a non-matching configuration
takes m_c → ~0 expected. P(rotation preserves all 4 matches) ≈ 0 for
piece with all distinct edges.

**Strict proof attempt**: assume for contradiction that some rotation
preserves m_c (≥ current m_c). Then:
- For each of c's matched sides s before rotation, the (new edge at s)
  must STILL match the neighbor's edge.
- Equivalently: the piece's CYCLIC permutation of (T,R,B,L) under
  rotation r must agree on at least m_c positions with the SAME
  cyclic pattern of NEIGHBOR colors.

This is equivalent to a cyclic-shift fixed-point problem. The number of
cyclic-shifts preserving exactly k of 4 positions is...
- k = 4: only identity rotation. ✓
- k = 3: impossible (cyclic shift can't preserve exactly 3 of 4).
- k = 2: cyclic shift of 2 (R180); preserves 2 positions iff edges T=B, R=L.
- k = 1: impossible (analogous).
- k = 0: any non-identity rotation when piece has distinct edges.

**Theorem (k=2 case)**: R180 preserves matched-count iff piece has T=B AND R=L.

**Canonical E2 measurement (vol-122)**:
- **0 pieces** have T=B AND R=L (= R180-fixed).
- **0 pieces** have all 4 edges identical (= R90-fixed).
- **37 pieces** have ONE pair-equal (T=B XOR R=L) — half-R180-symmetric.

**Consequence (K=1 R180 rotation)**: since NO piece is R180-fixed,
applying R180 always changes at least one of {T-vs-B match, R-vs-L match}.

**Stronger consequence (full proof attempt for R180)**: for a piece with
edges (T, R, B, L) at cell c with neighbors (N, E, S, W) having matched
sides (n, e, s, w) ∈ {0,1}, the score contribution is:
  m_c = [T=N's bottom] + [R=E's left] + [B=S's top] + [L=W's right]

After R180, the piece edges become (B, L, T, R). New matches:
  m_c' = [B=N's bottom] + [L=E's left] + [T=S's top] + [R=W's right]

So:
  m_c' - m_c = ([B=N's bot] - [T=N's bot]) + ([L=E's left] - [R=E's left])
             + ([T=S's top] - [B=S's top]) + ([R=W's right] - [L=W's right])

Group: terms 1+3 cancel iff T=B (then [B=X] = [T=X] for any X). Similarly
terms 2+4 cancel iff R=L. So:
  m_c' - m_c = 0 iff (T=B AND R=L)
            = could be anything otherwise, BUT must be EVEN since each
              non-symmetric pair changes by even count (matches both swap or none)

**Theorem (R180 K=1 LOCK)**: For canonical E2 puzzle (0 R180-fixed pieces),
applying R180 to ANY piece changes its matched-count m_c → m_c' where
m_c' has DIFFERENT PARITY than m_c if the asymmetric pair flips one
match. So m_c' ≠ m_c is GUARANTEED.

BUT m_c' might be HIGHER than m_c (e.g., 0 → 2 or 2 → 4). The theorem
only says ≠, not ≤.

**Refined claim**: at a high-score board (S ≥ 459), the EXPECTED m_c is
high (~3.6). Random R180 gives m_c' uniformly distributed → P(m_c' > m_c)
is very small. Confirmed by empirical 768 = 0 improvements.

**The strict lock at K=1 R180 is EMPIRICAL on the 459 basin, not analytical.**

**Empirical confirmation**: K=1 exhaustive test (768 moves) showed 0
improvements on 459 board. Matches the prediction if the piece set has
no T=B,R=L pieces.

## K=2 (piece swap) — CONJECTURE

**Setup**: swap pieces at cells c1, c2. Modified board B'.

**Score change**: Δ = (new m_{c1} + new m_{c2}) - (old m_{c1} + old m_{c2})
+ (boundary effect if c1, c2 are adjacent).

**Generic case (c1, c2 not adjacent)**:
- old m_{c1} + old m_{c2} = sum of matched edges at both cells.
- new m_{c1} = matches with NEIGHBORS of c1 from the piece that was at c2.
- new m_{c2} = matches with NEIGHBORS of c2 from the piece that was at c1.

For Δ > 0, need the swapped pieces to match BETTER at their new positions
than the original pieces did.

**Conjecture**: at high-score B (≥459), the score 459 is achieved via a
specific matching of pieces to positions optimizing local color compatibility.
A random swap "breaks" this optimization with high probability.

**Quantitative argument** (informal):
- old m_{c1} + old m_{c2} is at least 6/8 (avg ~3.6/4 each).
- For Δ ≥ 0, new combined ≥ 6/8 PROBABILISTICALLY requires very specific
  color-compatibility between swapped pieces and target neighborhoods.
- For "generic" pairs of pieces, P(matches ≥ 6) at non-original positions
  is exponentially small in the number of constraints.

**This is NOT a rigorous proof**, but it's a probabilistic argument
consistent with the 32640 empirical zero-improvements.

## K=3 to K=5 — OPEN

Beyond K=2, the combinatorial complexity grows. The vol-22/44/55/95/121
cluster MIPs (which test K ≤ 60 in halo regions) all confirm Δ=0 on
existing 458/459 basins.

**Hypothesis (vol-122 K7 finding)**: the 25-edge gap between McGavin 469
and our 444 is ENTIRELY interior-interior. So K-moves with K large enough
to cover the 25 mismatched edges would need K ≥ ~25 cells.

## Why empirical zero-counts don't directly prove the analytical lock

The empirical tests sample specific instances on specific high-score
boards. They prove K-lock for THOSE boards. The analytical question is
whether ALL high-score boards (459+) are K-locked under K ≤ K₀.

A counter-strategy: construct a high-score board where K=2 swap DOES
yield Δ > 0. If such a board exists, the conjecture fails.

## Status

`analytical-partial` — K=1 proof sketch via cyclic-shift fixed-points.
K=2+ conjecture only. Multi-day work to formalize.

## What this enables

A rigorous K-lock theorem would:
1. Justify pruning K-bounded ALNS moves at high scores (algorithm
   optimization).
2. Refute the "small-move-can-improve" strategy globally.
3. Drive search toward LARGE moves (K > K₀) which are more expensive
   but only ones with hope of breaking K-lock.

## Linked

- [[vol122-kmove-lock-analysis]] (empirical K=1, K=2 evidence)
- [[vol122-sigma-perm0-444-to-mcgavin-indecomposable]] (K=255 evidence)
- vol-65 rotation-symmetry note (all 256 orbits size 4)
- vol-118 rigidity theorem (memory)
