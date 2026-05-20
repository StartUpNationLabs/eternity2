---
name: w1-canonical-scale-plan
description: "Roadmap for scaling W1 PEPS-Lagrangian to canonical 16×16. Phase 1 (DONE): Python validation on 4×4/6×6. Phase 2 (NOW): Python multiprocessing. Phase 3 (next): full Rust port with PyO3 fallback for contraction. Phase 4: canonical run."
metadata:
  type: project
status: partial
---

# W1 — Canonical scale roadmap

After validating W1 on 4×4 (1s) and 6×6 (5min) in Python with quimb backend,
we need to scale to canonical 16×16 (K=23). This page is the plan.

## Bottleneck analysis (Python serial, 6×6)

| Operation | Time | Notes |
|-----------|------|-------|
| Single full contraction (log_Z) | ~30ms | Quimb boundary_mps, chi=128 |
| Single opened contraction | ~30ms | Same scale |
| Per Lagrangian iter | ~1 s | 36 cells × 30ms = ~1.1 s |
| Lagrangian convergence | ~30 iter avg | early rounds ~70 iter, late rounds ~1 iter |
| Single piece-fixing round | ~30 s avg | Variance 1-70s |
| Full 6×6 solve | ~5 min | 36 cells × ~10s/round avg |

Bottleneck: **the per-cell opened contractions**. They dominate
because we do n_cells × n_iter × n_rounds of them. For 6×6: 36 × 30 × 36 ≈ 40k contractions.

## Scaling projection to canonical 16×16, K=23

- Per contraction: ~1 sec (extrapolating; K=23 vs K=8, lattice size 16² vs 6²)
- Iter cost: 256 × 1s = 256 s = 4 min
- Convergence iter: ~200 (more pieces → harder dual)
- Per round: 200 × 4 min = 13 hours
- Total full solve: 256 × 13 hours = 140 days serial

**Untenable.** Need either:
(a) Better scaling per contraction (e.g., GPU-accelerated quimb).
(b) Parallelization across the 256 opened contractions per iter.
(c) Skip full solve; do 1 dual round → marginals → CSP value-order.

## Phase 2: Python multiprocessing (IN PROGRESS)

Each Lagrangian iter has n_cells opened contractions. Embarrassingly parallel.
- Run on N cores → ~N× speedup per iter.
- 10-core MacBook → 13 hours / 10 = 1.3 hours per round → ~14 days canonical.

Implementation: `scripts/w1_peps/peps_quimb_parallel.py`. Works on 4×4 (1.1s);
6×6 running now in background.

**This is the fastest path to canonical-scale runs.**

## Phase 3a (parallel track): Full Rust port

Goals:
1. Cell tensor building in Rust (parallel via Rayon). ALREADY WORKS (`crates/peps/src/tensor.rs`).
2. Boundary-MPS contraction in Rust with chi-truncation. **STUCK** (chain-contraction bugs).
3. Lagrangian dual loop in Rust orchestrating everything.

Status: Step 1 works (3/3 tests pass). Step 2 doesn't (4×4 returns -inf vs 5.9135).

Lessons learned trying step 2:
- ndarray + ndarray-linalg + openblas-src links correctly with custom build.rs.
- The chain-contraction algorithm has many implicit bond-order invariants
  that are easy to get wrong. Three separate attempts produced wrong results.
- Quimb's TN2D abstraction encapsulates this; reimplementing from scratch
  requires either reading quimb's source carefully or using a different approach.

Path forward (Phase 3a): Read quimb's `_contract_boundary_core` and
`contract_boundary_from_*` sources, replicate the exact MPS canonicalization
strategy in Rust. Multi-week effort.

## Phase 3b: Rust + PyO3 hybrid

Alternative to full port:
1. Rust builds cell tensors (parallel, fast).
2. Convert to numpy via PyO3 / `pyo3-numpy`.
3. Call quimb (via Python) for the contraction.
4. Read back the result tensor.
5. Rust loops the Lagrangian dual.

Wins over pure Python:
- ~10x speedup from parallel cell-tensor building in Rust.
- ~10x speedup from Rust orchestrating without Python overhead.
- Plus parallel opened contractions via Rayon at the Rust level
  (each thread calls Python independently with GIL released).

Risk: PyO3 setup complexity; GIL releasing during quimb calls.
Effort: ~3 days for working hybrid.

## Phase 4: Canonical 16×16 run

Once Phase 2 or Phase 3 is operational:
1. Single Lagrangian dual run (no piece-fixing) on canonical puzzle.
   Dump per-cell-piece-rotation marginals. Cost: ~1-2 days.
2. Feed marginals as value-order to solver-engine CSP. Vol-12 BP gave 18%
   reduction; W1 marginals (with piece-uniqueness) should give MORE.
3. Concurrently: full sequential piece-fixing at canonical scale via parallel
   Phase 2/3 (~weeks).
4. ALNS basic 30min × N seeds on any partial board produced.
5. If any board reaches ≥ 460 matched-edges: standing record broken.

## Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Lagrangian doesn't converge at canonical scale | Adaptive eta, momentum, larger chi |
| chi=128 not enough for canonical accuracy | Try chi=256, chi=512 |
| Memory exhaustion at chi=512 | RAM upgrade, or chi=256 with looser tol |
| ALNS doesn't lift partial to ≥460 | Run multiple basins, multiple seeds |
| Solver-engine CSP-with-PEPS-marginals not faster | Compare to BP value-order baseline |

## What's been validated

- Algorithm correctness (4×4 + 6×6 complete solves verified).
- Vol-13 piece-uniqueness obstruction solved (Lagrangian dual).
- Chi=32 too small for 6×6+; chi=128 stable.
- Sequential piece-fixing accelerates as cells get pinned.

## Open questions

- Does chi=128 generalize to K=23 canonical? Empirical question.
- Does the dual converge on canonical-scale puzzles? Empirical question.
- Will the marginals correlate with the actual solution? Empirical question.
- Best initial-fix order: random vs. most-peaked vs. spatially-correlated?

## Linked

- [[w1-peps-design-derivation]]
- [[w1-peps-empirical-results]]
- [[web-roam-2026-05-17]] (W1 source)
- [[boundary-mps]] (vol-13 refutation that W1 solves)
