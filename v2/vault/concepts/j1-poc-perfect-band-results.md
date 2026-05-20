---
name: j1-poc-perfect-band-results
description: "J1 column-DP PoC achieves PERFECT band-0 score on every puzzle size tested (4x4 through canonical 16x16). Beam=5000 finds optimal 2-row arrangement maximizing all adjacencies."
metadata:
  type: project
status: built
---

# J1 — PoC PERFECT-band results

## Summary

Double-row column-DP with beam search achieves **maximum possible
band-0 score on every puzzle tested**:

| Puzzle | Colors | Pieces | Max possible | Achieved | Time |
|---|---|---|---|---|---|
| 4×4 | 2 | 16 | 10 | **10/10** ✓ | 0.1s |
| 4×4 | 4 | 16 | 10 | **10/10** ✓ | 0.0s |
| 5×5 | 3 | 25 | 13 | **13/13** ✓ | 0.5s |
| 5×5 | 4 | 25 | 13 | **13/13** ✓ | 0.2s |
| 6×6 | 4 | 36 | 16 | **16/16** ✓ | 1.2s |
| 6×6 | 5 | 36 | 16 | **16/16** ✓ | 0.6s |
| 7×7 | 4 | 49 | 19 | **19/19** ✓ | 4.0s |
| 8×8 | 5 | 64 | 22 | **22/22** ✓ | 6.5s |
| 8×8 | 6 | 64 | 22 | **22/22** ✓ | 4.2s |
| 8×8 | 7 | 64 | 22 | **22/22** ✓ | 3.1s |
| 8×8 | 8 | 64 | 22 | **22/22** ✓ | 1.6s |
| 10×10 | 10 | 100 | 28 | **28/28** ✓ | 5.5s |
| 12×12 | 12 | 144 | 34 | **34/34** ✓ | 11.8s |
| **16×16** | **23** | **256** | **46** | **46/46** ✓ | **68s** |

Max-possible = $3 \cdot \text{side} - 2$ = 1 initial vertical + 2 horiz + 1
vertical per column-step × (side-1) column-steps.

## Algorithm

State at column $j$: $(p_t, r_t, p_b, r_b, \mathcal{U}_j, \text{score}_j)$
where $p_t, p_b$ are top/bottom pieces, $r_t, r_b$ rotations,
$\mathcal{U}_j$ used-piece set, $\text{score}_j$ cumulative matched edges.

Transition to column $j+1$: pick $(p_t', r_t', p_b', r_b')$ such that:
- $p_t'.L = p_t.R$ (top horizontal match)
- $p_b'.L = p_b.R$ (bottom horizontal match)
- $p_t'.B = p_b'.T$ (vertical match)
- $p_t', p_b' \notin \mathcal{U}_j$ and $p_t' \neq p_b'$.

Each match contributes 1 if color ≠ 0 (BORDER).

Beam-prune: keep top $K=5000$ states by score at each column.

## Counterintuitive scaling

**More colors = faster, not slower**:
- 8×8 c5: 6.5s
- 8×8 c8: 1.6s

Reason: more colors means tighter constraints (fewer feasible
transitions), so the beam contracts and fewer states need expansion.

This is OPPOSITE of FSMC (J6) where more colors hurts hit-rate. Here
the algorithm uses constraints DIRECTLY — they reduce search not via
state-collision but via dead-ends.

## Implications

For canonical 16×16, the FIRST 2-row band achieves 46 edges (out of 46
possible). That's a massive improvement over random initialization
which yields ~10 edges in 2 rows.

If we can **chain** 15 bands sequentially (using each band's bottom row
as next band's fixed top), and each band achieves ~45 edges on average,
the total = 15 × 45 ≈ 675 — but that double-counts shared rows. Each
band has 16 piece-columns × 2 rows. Total internal adjacencies per band
= 16 horizontal × 2 rows + 16 vertical = 47 (= max 46 + 1 boundary)

Actually max-possible per band = side × 2 horizontal + side × 1 vertical
between rows = $2 \cdot \text{side} \cdot 1 + \text{side} = 3 \cdot \text{side}$ ... let me recount.

Per band (2 rows × side cols):
- 2 × (side - 1) horizontal matches = 2(side - 1)
- side vertical matches between the 2 rows = side
- Total = 2(side - 1) + side = 3·side - 2

For side=16: 46. ✓

Total possible matches in full 16×16 board = 480.
Decomposed into 15 row-pairs: each band has 46 (horizontal × 2 + vertical between).
But the HORIZONTAL matches in row $r$ are counted in BOTH bands $r$ and $r+1$
if those bands are processed independently. So sum over 15 bands of (matches)
= 15 × 46 = 690 = 480 (target) + 210 (double-counted horizontal matches).

So per-band perfect doesn't directly map to full-board perfect.

The chained algorithm: band 0 commits ROWS 0, 1 (46 edges). Band 1
fixes row 1 (from band 0) and adds row 2 — its matches include horizontal
in row 2 + vertical between rows 1-2. New matches added per band 1+:
= 2(side - 1) + side - (side - 1) = side - 1 + side = 2·side - 1 = 31 (for side=16)
because horizontal in row 1 was already counted in band 0.

Wait this gets confusing. Let me think more carefully — see the chain
script for actual implementation.

## Status

`PoC-perfect-band-confirmed` for all puzzle sizes including canonical.

Next:
1. Complete chain on canonical 16×16 (in flight, 50min budget).
2. Verify chained full board against verify_board.
3. Rust port for performance (user noted).

## Linked

- [[j1-column-dp-design]] (algorithm design)
- [[vol-122]]
- [[INVENTIONS_BACKLOG]] J1 entry
