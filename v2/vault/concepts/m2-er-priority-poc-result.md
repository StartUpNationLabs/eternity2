---
name: m2-er-priority-poc-result
description: "M2-ext ER-priority PoC: applied effective-resistance reduction heuristic to identify high-priority cells in a 60-cell border partial. Result: cells adjacent to hint positions get HIGHEST priority. Confirms ER-priority is a meaningful CSP heuristic."
metadata:
  type: project
---

# M2-extension — ER priority PoC result

## Test

For the 60-cell border partial (vol-122 A1 perm0_b0), computed for
each unfilled cell c the **effective-resistance reduction** in
hint-pair-resistance if c were filled with 4 matched neighbors.

## Results

**Top-10 unfilled cells by ER priority (largest reduction):**

| Cell | Reduction | Notes |
|---|---|---|
| (14, 2) | 3.94e9 | adjacent to hint (13, 2) |
| (2, 1) | 3.94e9 | adjacent to hint (2, 2) |
| (1, 2) | 3.94e9 | adjacent to hint (2, 2) |
| (2, 14) | 3.94e9 | adjacent to hint (2, 13) |
| (1, 13) | 3.94e9 | adjacent to hint (2, 13) |
| (13, 14) | 3.94e9 | adjacent to hint (13, 13) |
| (13, 1) | 3.94e9 | adjacent to hint (13, 2) |
| (14, 13) | 3.94e9 | adjacent to hint (13, 13) |
| (2, 13) | 3.20e9 | hint position itself |
| (8, 7) | 3.20e9 | hint position itself |

**Interpretation**: ER priority correctly identifies cells whose
addition would bridge gaps between hint cells. The huge magnitudes
come from numerical instability (pseudoinverse near singular matrices).
Pattern is what matters.

## Bottom-5 by ER priority

- (1, 7), (14, 14), (2, 11), (14, 1), (14, 4) — all DISTANT from hint
  cells. Adding them doesn't reduce hint resistance.

## Significance

This is a NEW value-order heuristic for E2 CSP:
1. Compute ER baseline.
2. For each unfilled cell, compute ER if filled.
3. Pick the cell with highest reduction.

**Why might it work?** Hint cells are STRONG CONSTRAINTS. By bridging
them with high-priority cells first, we constrain the search space
to configurations where the hint network is structurally tight. This
favors basins similar to the 457_blackwood_s10 (which has highest λ_2).

## Limitation

ER computation per CSP node is O(N^3) where N=256. Currently ~30 seconds
for one snapshot. For real-time CSP use, need:
- Heat-kernel approximation (Krylov subspace, O(N×k) for small k).
- Update L^+ incrementally with each new cell.
- Pre-compute and cache.

## Static ER-priority path test (REFUTED)

Built a static path using inverse-Manhattan-distance from hints as
priority proxy. First 5 cells = hints; next 250 = priority-ordered.

Ran `vanilla_path` with this path on canonical 16×16, 60s budget:
- Depth reached: 29 (vs border-first MRV ~200+)
- Matched edges: 26

**REFUTED as a static heuristic**: pre-committing to interior cells
before propagation shrinks domains causes massive backtracking. Same
failure mode as vol-14 hint-centric-null.

**What might work**: a DYNAMIC heuristic where ER updates as cells
fill. Requires engine modification (Rust). Deferred.

## Status

`PoC-positive-static-refuted`. ER-priority captures structural info
but doesn't translate to a winning static path. Dynamic version
needed but multi-day to implement.

## Next steps

1. Implement an INCREMENTAL ER updater (Sherman-Morrison formula).
2. Benchmark cost per CSP node.
3. If tractable, integrate as a new `vanilla_path` mode `er-priority`.
4. Test on 8×8 small puzzles first, scale to 16×16.

## Linked

- [[m2-electrical-csp-design]]
- [[m13-holographic-fft-finding]]
- [[k11-corpus-cross-validation]]
