---
name: piece-tensor-spectroscopy
description: "Vol-216 (live Q&A): the canonical E2 piece set as a 23^4 4-tensor is ANOMALOUSLY FLAT — top Tucker singular values below the random-control p5, effective rank 16.96 above the control p95 [16.67, 16.83] (controls = random piece sets with identical side-color histogram). The piece tensor is more incompressible than chance: low-rank/algebraic shortcuts are foreclosed by design. N-S side-pair MI sits at the p5 edge (the rare-opposite rule's fingerprint)."
status: built
metadata:
  type: concept
---

# Piece-tensor spectroscopy

**Origin**: vol-216, live analysis during user Q&A on multi-dimensional
methods. **Files**: inline analysis (session transcript); re-runnable
in ~30 s from `scripts/v216_lp/lp_prefix_score.py` loaders.

## Definition

The 196 interior pieces form a sparse 4-tensor
$T[n][e][s][w] \in \mathbb{N}^{23^4}$ (784 nonzeros over all
rotations). The full puzzle is a 2D contraction network of copies of
$T$ — so $T$'s algebraic structure bounds what shortcuts can exist.
Tucker mode spectra (SVD of mode unfoldings, 23×23³) and side-pair
mutual information, compared against 20 random piece sets with the
SAME side-color histogram.

## Measurements (canonical Selby-Riordan set)

| statistic | E2 | random controls [p5, p95] |
|---|---|---|
| top mode-0 singular values | 7.30, 7.11, 7.03 | medians 7.86, 7.61, 7.45; p5 7.62, 7.46, 7.29 |
| **effective rank** (spectral entropy) | **16.96** | 16.75 [16.67, 16.83] |
| N-S (opposite side) MI | 0.1752 | 0.1942 [0.1745, 0.2321] |
| N-E (adjacent side) MI | 0.1857 | 0.1976 [0.1622, 0.2164] |

## Findings

1. ★ **The piece tensor is anomalously HIGH-rank / flat**: leading
   singular values are suppressed BELOW the random p5 and effective
   rank sits ABOVE the random p95. The canonical set is *more
   incompressible than chance* given its color frequencies — the
   spectral signature of a design optimized against algebraic
   structure (consistent with: zero rotation-symmetric pieces, the
   [[rare-opposite-rule]], distinctness-driven hardness per
   [[isentrope-entropy-growth]]).
2. **Consequence**: no low-rank color embedding exists — "embed colors
   in a small vector space where matching ≈ inner product" shortcuts
   (fast algebraic propagation, spectral whole-board relaxations) are
   foreclosed BY THE PIECE SET, not merely unfound. Don't spend a
   volume looking for one.
3. N-S MI at the p5 edge = the mild fingerprint of the rare-opposite
   rule; otherwise the tensor is statistically near-generic.

## Linked

[[isentrope-entropy-growth]], [[assignment-lp-prefix-scoring]],
session [[vol-216]]
