// Lagrangian dual driver for PEPS piece-uniqueness.
//
// STATUS: STUB. The full implementation requires the boundary-MPS contractor
// (mps.rs) to be operational. The algorithm is:
//
//   μ ← 0
//   for iter:
//     Z_full = boundary_mps_contract(PEPS(μ), chi)
//     for each cell i:
//       Z_i^open = boundary_mps_contract(PEPS(μ) without cell i, chi)
//     q_p = Σ_i Σ_rot exp(-μ_pid) * Z_i^open[sig(pid,rot)] / Z_full
//     if max|q-1| < tol: break
//     μ ← μ + η * (q - 1)
//
// Sequential piece-fixing:
//   pinned = {}
//   while len(pinned) < n_cells:
//     run Lagrangian on PEPS with `pinned`
//     find cell, pid, rot with max P_i(piece=pid, rot)
//     pinned[cell] = (pid, rot)
//
// Reference: vault/concepts/w1-peps-design-derivation.md
//            vault/concepts/w1-peps-empirical-results.md
//            scripts/w1_peps/peps_quimb_lagrangian.py

use crate::PepsContext;

/// Placeholder.
pub fn lagrangian_dual(_ctx: &PepsContext, _chi: usize, _max_iter: usize) -> Vec<f64> {
    vec![]
}
