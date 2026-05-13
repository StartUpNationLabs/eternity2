---
tags: [concept, message-passing, value-order]
status: refuted-as-value-order, used-in-pipeline
origin-vol: 11
---

# BP marginals (belief propagation as value-order)

**Status**: `refuted` as standalone value-order (vol-11, vol-12); `partial-positive` inside pipeline (vol-14)
**Origin**: vol-11 (cell encoding), vol-12 (edge encoding)
**Files**: `scripts/v11_bp.py`, `scripts/v12_edge_bp.py`, `crates/solver-engine/src/lib.rs` (`ValueOrder::EdgeBpMarginals`, vol-14)

## Setup (vol-11, cell encoding)

- **Variables**: 256 cell positions, domain = (piece_id, rotation) tuples class-compatible with the cell's border mask. Total ~152,901 states.
- **Factors**: 480 pairwise edge-equality constraints across grid joins.
- **Piece-uniqueness**: soft, via per-piece availability reweighting between BP iterations (hard alldiff over 256 pieces is intractable for BP).

## Vol-11 measurements (cell encoding)

- Damping 0.3, converges in ~60 iterations, ~1.4 s in Python.
- Hint cells reach entropy H=0 correctly.
- Mean per-cell entropy reduction at convergence:
  - corner: 0.7% reduction
  - edge: 3.0% reduction
  - interior: **8.4% reduction**

## Backtracker A/B (BP marginals as value-order, 90s budget)

| value mode | max_depth | max_score | nodes | backtracks |
|---|---:|---:|---:|---:|
| bp | 157 | 256 | 16k | 27k |
| static | 154 | 263 | 17k | 33k |
| **random** | **173** | **297** | 14k | 25k |

**Random outperforms BP and static.** BP marginals add no value-order advantage in plain backtracking. Likely cause: deterministic value orders correlate failure modes.

## Vol-12 edge-color BP (different encoding)

- 544 edges × 23 color states.
- **18.84% interior reduction** (2.24× cell-encoding).
- Python A/B: BP value-order gets depth 67 / score 65 vs random depth 66 / score 62.

→ **First BP-marginals variant to BEAT random as value-order**, in Python. Ported to Rust as `ValueOrder::EdgeBpMarginals` in vol-14.

## Vol-14 Rust port — empirical reversal

- **CP-only**: EdgeBpMarginals at 5min loses to baseline by −3 depth, −11 matched.
- **End-to-end (CP + ALNS-fill)**: EdgeBpMarginals wins 443/480 vs baseline 442/480 (on broken-ALNS-hint-pinning binary; corrected post-bug to ~440 baseline).

→ Net positive in pipeline; pure value-order axis exhausted.

## SP-y (1RSB) sweep over Parisi parameter m

| m | interior reduction |
|---|---|
| 1.0 (≡ BP) | 8.3% |
| 0.8 | 7.9% |
| 0.5 | 7.5% |
| 0.30 | 7.3% |
| 0.15 | 7.0% |

**Lower m → flatter marginals, not sharper.** Reversed from random k-SAT. Confirms E2's solution landscape is NOT 1RSB-shattered; SP collapses to BP at best. See [[survey-propagation]].

## Why BP fails on E2

- E2's factor graph has short cycles (every 2×2 block) → BP messages don't decorrelate.
- 5 hints are below the rigidity threshold → marginals are nearly uniform.
- The empirical analog (Edwards-Anderson spin glass on 2D grid) has the same glassy plateaus.

## What's still potentially viable (unbuilt)

- **CVM / generalized BP on 2×2 plaquettes**: ~225 plaquettes × ~10⁴ states each. Captures short-range correlations BP misses. Marginally tractable.

## Linked concepts

- [[survey-propagation]] — 1RSB extension, same negative verdict
- [[boundary-mps]] — vol-13 tensor-network analogue, also bounded
- [[blackwood-algorithm]] — orthogonal direction that worked

## Linked memory

- `reference_e2_bp_measurements`
- `project_e2_edge_bp_measurement`
- `project_e2_vol14_bp_null`
