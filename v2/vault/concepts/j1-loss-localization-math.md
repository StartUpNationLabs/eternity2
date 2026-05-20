---
name: j1-loss-localization-math
description: "J1 chain loss is ENTIRELY in vertical color matches between rows 8-14, not in horizontal matches. All 14 inner rows have PERFECT horizontals matched. Mathematically derived from total-edge accounting."
metadata:
  type: project
status: built
---

# J1 — Localization of chain loss

## Setup

J1 Rust chain (beam=100k) gives:
- Final board: 256/256 placed, **444/480 matched**.
- Band scores: $\{S_r\}_{r=0}^{14}$ = $\{46, 46, 46, 46, 46, 46, 46, 46, 45, 45, 43, 42, 40, 36, 35\}$.
- Sum of band scores: 654.

## Math: relating sum-of-band-scores to full-board score

For an $n \times n$ board, let:
- $H_r$ = # matched horizontals in row $r$ (max $n-1$ per row)
- $V_r$ = # matched verticals between rows $r$ and $r+1$ (max $n$)

Per band:
$$
S_r = H_r + H_{r+1} + V_r
$$

Summing:
$$
\sum_{r=0}^{n-2} S_r = \sum_{r=0}^{n-2}(H_r + H_{r+1} + V_r) = H_0 + H_{n-1} + 2\sum_{r=1}^{n-2} H_r + \sum_{r=0}^{n-2} V_r
$$

Full board:
$$
E = \sum_{r=0}^{n-1} H_r + \sum_{r=0}^{n-2} V_r
$$

Hence:
$$
E = \sum_{r=0}^{n-2} S_r - \sum_{r=1}^{n-2} H_r
$$

## Application to J1 chain

$\sum S_r = 654$ and $E = 444$. So:
$$
\sum_{r=1}^{n-2} H_r = 654 - 444 = 210
$$

For $n = 16$: $\sum_{r=1}^{14} H_r = 210$. Max possible per row is $n-1 = 15$. So $14 \times 15 = 210$.

**$\sum_{r=1}^{14} H_r = 210 = 14 \times 15$ → ALL inner row horizontals are perfectly matched.**

## What's missing then?

$E_{\text{missing}} = 480 - 444 = 36$ edges.

Components of missing edges (not in inner-row horizontals):
- $H_0$ (top row): max 15. Achieved $H_0 = ?$
- $H_{n-1} = H_{15}$ (bottom row): max 15. Achieved?
- $\sum_{r=0}^{14} V_r$ (verticals): max 16 × 15 = 240. Achieved?

From band 0 perfect ($S_0 = 46$): $H_0 + H_1 + V_0 = 46$. We have $H_1 = 15$. So $H_0 + V_0 = 31$. Max: $15 + 16 = 31$. **$H_0 + V_0 = 31$ → both perfect.**

From band 14 = 35: $H_{14} + H_{15} + V_{14} = 35$. We have $H_{14} = 15$. So $H_{15} + V_{14} = 20$. Max: $15 + 16 = 31$. **Missing 11 edges in row 15 horizontals + V_14 verticals.**

Similarly band 13 = 36: $H_{13} + H_{14} + V_{13} = 36$. $H_{13} = H_{14} = 15$. So $V_{13} = 6$. Max $V_{13} = 16$. **Missing 10 verticals.**

Band 12 = 40: $V_{12} = 40 - 30 = 10$. Missing 6 verticals.
Band 11 = 42: $V_{11} = 42 - 30 = 12$. Missing 4 verticals.
Band 10 = 43: $V_{10} = 43 - 30 = 13$. Missing 3.
Band 9 = 45: $V_9 = 45 - 30 = 15$. Missing 1.
Band 8 = 45: $V_8 = 15$. Missing 1.
Bands 0-7 (all 46): $V_0, \ldots, V_7 = 16$ each. All perfect.

## Loss distribution

| Component | Lost | Max | Perfection |
|---|---|---|---|
| $H_0$ (top row) | 0 | 15 | ✓ perfect |
| $H_1 \ldots H_{14}$ (inner rows) | 0 | 210 | ✓ perfect |
| $H_{15}$ (bottom row) | $11 - V_{14}$ | 15 | ? |
| $V_0 \ldots V_7$ | 0 | 128 | ✓ perfect |
| $V_8$ | 1 | 16 | -1 |
| $V_9$ | 1 | 16 | -1 |
| $V_{10}$ | 3 | 16 | -3 |
| $V_{11}$ | 4 | 16 | -4 |
| $V_{12}$ | 6 | 16 | -6 |
| $V_{13}$ | 10 | 16 | -10 |
| $V_{14} + H_{15}$ | 11 | 31 | -11 |

**Total loss: 36 edges, ALL in vertical matches between rows 8-15 + the bottom row horizontals.**

## Key insight

The chain greedy doesn't lose horizontals — it loses **VERTICAL color
matches** in the late bands. Mathematically:

- Top row $H_0$: forced perfect by border constraints + band 0 perfect score.
- Inner rows $H_r$: perfect because bands have to commit row pairs, the horizontals
  are paired with the band's free-bottom-row.
- $V_r$ for $r \leq 7$: perfect because top row anchors with strong color constraints.
- $V_r$ for $r \geq 8$: degraded because the chain's accumulated commitments
  fail to provide compatible vertical color profiles.

## Implication for forward-look heuristic (FLH)

The FLH should specifically optimize for VERTICAL color matches in
future bands, not just current-band score. Specifically, when band $r$
chooses its bottom row, the chosen colors at the bottom edge of each
cell should match SOME remaining piece's TOP edge.

## Status

`obstruction-precise-math` — exact loss localization derived.

## Linked

- [[j1-rust-beam100k-first-complete-board]]
- [[j1-forward-look-heuristic]]
- [[j1-column-dp-design]]
