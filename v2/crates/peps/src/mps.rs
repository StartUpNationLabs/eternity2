// Boundary-MPS contraction with chi-truncation — placeholder Rust module.
//
// STATUS: STUB. The validated Python implementation in
// scripts/w1_peps/peps_quimb_lagrangian.py uses quimb for boundary-MPS
// contraction. A full Rust port requires:
//   1. ndarray-linalg with LAPACK for SVD
//   2. A custom row-by-row MPS absorption algorithm
//   3. Integration with cotengra-style contraction-path optimization
//      (or pure greedy)
//
// For Phase 2, the recommended path is:
//   (a) Keep the Python implementation as the primary algorithm.
//   (b) Parallelize the per-cell opened contractions via Python
//       multiprocessing.Pool (immediate ~10x speedup).
//   (c) If still bottlenecked, port to Rust as a dedicated crate using
//       tensor primitives, possibly via tch-rs (LibTorch) or candle.
//
// The Rust cell-tensor builder (tensor.rs) and Lagrangian dual driver
// (lagrangian.rs) are both feasible to port; the boundary-MPS engine is
// the main blocker.
//
// Reference: vault/concepts/w1-peps-design-derivation.md

use crate::PepsContext;

/// Placeholder. Returns NaN to indicate unimplemented.
pub fn log_z_exact(_ctx: &PepsContext, _mu: &[f64], _pinned: &[Option<(u16, u8)>]) -> f64 {
    f64::NAN
}
