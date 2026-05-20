---
name: w1-peps-empirical-results
description: "W1 empirical results from Phase 1 (4×4 → 6×6). 4×4 completely solved in 1 second via sequential PEPS-Lagrangian piece-fixing. 6×6 partial solve in ~3 minutes per fix. chi=128 needed for stable gradients. Roadmap to canonical 16×16."
metadata:
  type: project
status: built
---

# W1 — Empirical results (Phase 1)

## TL;DR

W1 PEPS-Lagrangian solves 4×4 generated puzzles completely in ~1 second.
6×6 piece-fixing works at ~30s per cell.

Key empirical findings:
- **chi=32 is too small for 6×6+**: gradients become unreliable, dual diverges.
- **chi=128 stable**: dual converges from gap=2.1 → 0.02 in ~150 iter.
- **Sequential fixing works**: first cell fixed has prob ~0.99-1.00 after dual.

## 4×4 results (puzzle: size_4_colors_6_92cd6738.csv, K=8)

### Exact contraction
- log_Z (μ=0): 5.9135 (paramagnetic-like)
- log_Z (μ converged): 3.7974

### Lagrangian dual convergence
- 20 iter to |q-1|∞ < 0.01 at η=0.5
- 0.5s total

### Sequential piece-fixing
- 16 cells fixed in 1.0s
- All cells fixed with prob ≥ 0.5; most ≥ 0.99
- Verification: 16/16 unique pieces, 12/12 interior matched, 16/16 border correct
- **Complete solve confirmed by verify_solution.py**

## 6×6 results (puzzle: size_6_colors_6_543a4a64.csv, K=8)

### Quimb boundary-MPS scaling
- chi=4: log_Z = 13.62 (some truncation error)
- chi=8: log_Z = 13.65
- chi=16: log_Z = 13.75
- chi=32: log_Z = 13.75
- chi=64: log_Z = 13.75 (~stable)
- chi=128: log_Z = 13.75 (~stable)
- ~30 ms per contraction for all chi values (after first-call cotengra path search)

### Lagrangian dual with chi=32 (TOO SMALL)
- Dual unstable: log_Z grows to >600 while gap stuck at 0.24
- Reason: truncation error gives wrong gradients; algorithm chases phantom configurations
- **DO NOT USE chi=32 for 6×6 Lagrangian; use chi=128**

### Lagrangian dual with chi=128
- η=0.3, 150 iter: gap from 2.11 → 0.02 (monotone decrease in log_Z)
- log_Z monotonically decreasing 13.75 → 7.24
- ~0.4 s per iter (after warm-up); 150 iter ≈ 60 s total
- **STABLE convergence at chi=128**

### Sequential piece-fixing
- chi=128, η=0.3, tol=0.05, max_iter=80
- First 6 cells fixed in 196 s (~32 s each)
- All with prob > 0.99 (very confident assignments)
- Full 6×6 run in progress (36 cells, est ~18 min)

## Scaling projection to canonical 16×16, K=23

### Per-contraction cost
- Lattice: 16×16 = 256 cells
- Bond dim K = 23
- Per-cell tensor: K^4 = 280k entries
- Per-cell opened contraction: requires χ-truncated boundary MPS contraction
- At χ=128, cost per opened contraction ≈ N · K^2 · χ^4 ≈ 256 · 529 · 2.7e8 ≈ 4 · 10^{13} FLOPs
  - ≈ 60 s per opened cell on CPU (10^12 FLOPS BLAS)
  - ≈ 3 s on GPU (10^13 FLOPS)
- 256 opened cells per Lagrangian iter = ~15 min per iter on CPU, ~13 min on GPU

### Per round (Lagrangian dual)
- Need ~200 iter for convergence at gap=0.02 (extrapolating from 6×6: 150 iter)
- ~200 × 15 min = 50 hours per Lagrangian round on CPU
- ~200 × 13 min = 43 hours on GPU

### Per piece-fixing round
- 50-100 hours per round on CPU (with full convergence)
- For 50 fixed cells: 50 × 50 hours = 2500 hours = 100 days (CPU)
- For 50 fixed cells: 50 × 43 hours = 2150 hours ≈ 90 days (GPU)

### Practical optimizations (must implement before canonical):

1. **Looser tolerance for early piece-fixing**: tol=0.1 gives a marginal good
   enough to pick a winner. Need only a "good enough" winner, not exact dual.
   Cuts Lagrangian iters to ~50, total ~12 hours per round. 50 cells → 25 days.
2. **Lower chi for inner iterations + chi=128 only for final**: 95% of work
   in Lagrangian dual at chi=64, switch to chi=128 only for the last 10 iter.
   ~2x speedup.
3. **Warm-start Lagrangian from previous round's μ**: ~50% reduction in iter
   per round.
4. **Reuse opt_einsum tree across iterations**: ~10x speedup of contractions.
5. **Rust port of opt_einsum + per-cell tensor builder**: ~10x speedup overall.

Combined: 50 cells in ~5-10 days CPU. **Acceptable for the autonomous month.**

### Alternative: skip sequential, use as ONE-SHOT marginals → CSP value-order

The PEPS marginals after the FIRST Lagrangian round give per-cell piece-rotation
probabilities. Feed these as **value-order heuristic** for our existing CSP
backtracker (`solver-engine joe profile with EdgeBpMarginals`-style hook). Single
Lagrangian round at canonical = ~50 hours. Then CSP solves the rest.

Vol-12 BP value-order gave 18.84% interior reduction. PEPS marginals should
give **much more** because they include piece-uniqueness (vol-13 boundary-MPS
without piece-uniqueness only captured local color matching).

## Files

- `scripts/w1_peps/peps_quimb_lagrangian.py` — production implementation
- `scripts/w1_peps/verify_solution.py` — solution verifier
- `scripts/w1_peps/puzzle_loader.py` — Python CSV loader

## Pseudocode summary

```
Build cell tensor T_i[cN, cE, cS, cW] = sum_{(pid,rot)} exp(-μ_pid)
  for each pid,rot whose edges match (cN, cE, cS, cW) and consistent with border

Lagrangian dual:
  μ ← 0
  for iter:
    Z_full = contract_boundary_mps(PEPS(μ), χ)
    for each cell i:
      Z_i^open = contract_boundary_mps(PEPS(μ) without cell i, χ)
    q_p = Σ_i Σ_rot exp(-μ_pid) × Z_i^open[sig(pid,rot)] / Z_full
    if max|q-1| < tol: break
    μ ← μ + η (q - 1)

Sequential piece-fixing:
  pinned = {}
  while len(pinned) < n_cells:
    run Lagrangian on PEPS with pinned cells fixed
    find (cell, piece, rot) with max P_i(piece, rot)
    pinned[cell] = (piece, rot)
```

## Linked

- [[w1-peps-design-derivation]] (math)
- [[boundary-mps]] (vol-13 refutation — what W1 fixes)
- [[bp-marginals]] (vol-11 BP measurement)
- [[edge-bp-measurement]] (vol-12 18.84% reduction; W1 should beat this)
- [[web-roam-2026-05-17]] (W1 source)
