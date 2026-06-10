// eternity2-peps — Rust port of W1 PEPS-Lagrangian for Eternity II.
//
// Algorithm overview (validated in Python via scripts/w1_peps/):
//
// 1. Encode the puzzle as a 2D tensor network (PEPS):
//    - Each cell (y, x) has a (K, K, K, K) tensor over (N, E, S, W) colors.
//    - Cell tensor T_i[cN, cE, cS, cW] = sum over (pid, rot) such that
//      piece(pid).rotated(rot).edges = (cN, cE, cS, cW), weighted by exp(-mu[pid]).
//    - Border-fixed axes have only one non-zero entry at BORDER=0.
//    - Adjacent cells share their bond axes (cell-i.E == cell-(i+1).W).
//
// 2. Run Lagrangian dual on piece-uniqueness:
//    - Z(mu) = trace(PEPS(mu))
//    - q_p = expected count of piece p across all cells
//    - Update mu_p ← mu_p + eta * (q_p - 1)
//    - Iterate until max |q_p - 1| < tol.
//
// 3. Sequential piece-fixing:
//    - At dual convergence, pick the (cell, piece, rot) with highest
//      probability. Pin it.
//    - Re-run dual with the pinned cell fixed.
//    - Repeat until all cells fixed or budget exhausted.
//
// Reference:
//   vault/concepts/w1-peps-design-derivation.md
//   vault/concepts/w1-peps-empirical-results.md
//   scripts/w1_peps/peps_quimb_lagrangian.py (validated Python)
//
// Phase 1 (this crate): full Rust port with parallel opened-cell contractions
// via Rayon, OpenBLAS-backed SVD for chi-truncation.

// Note: ndarray::s! macro uses unsafe internally, so we use deny instead of forbid.
#![deny(unsafe_code)]

use eternity2_core::{Puzzle, Rotation, BORDER};
use std::collections::HashMap;
use std::sync::Arc;

pub mod tensor;
pub mod mps;
pub mod mps_proper;
pub mod lagrangian;

/// Per-piece per-rotation signature: (N, E, S, W) colors.
pub type Signature = [u8; 4];

/// (piece_id, rotation) pair.
pub type PieceRot = (u16, u8);

/// Context for PEPS computations, shared across iterations.
pub struct PepsContext {
    pub puzzle: Arc<Puzzle>,
    /// piece_rotations[pid] = [Signature; 4] for the 4 rotations
    pub piece_rotations: Vec<[Signature; 4]>,
    /// Reverse lookup: Signature -> list of (pid, rot)
    pub signature_lookup: HashMap<Signature, Vec<PieceRot>>,
    /// K = max interior color + 1 (BORDER=0; interior = 1..K-1).
    pub k_colors: usize,
    /// Convenience: puzzle.width as usize.
    pub size: usize,
    /// Convenience: puzzle.pieces().len()
    pub n_pieces: usize,
}

impl PepsContext {
    pub fn new(puzzle: Arc<Puzzle>) -> Self {
        let n_pieces = puzzle.pieces().len();
        let mut piece_rotations = Vec::with_capacity(n_pieces);
        let mut signature_lookup: HashMap<Signature, Vec<PieceRot>> = HashMap::new();
        let mut max_color: u8 = 0;

        for (pid, piece) in puzzle.pieces().iter().enumerate() {
            let mut rotations = [[0u8; 4]; 4];
            for rot_idx in 0..4u8 {
                let rot = match rot_idx {
                    0 => Rotation::R0,
                    1 => Rotation::R90,
                    2 => Rotation::R180,
                    _ => Rotation::R270,
                };
                let edges = piece.edges.rotated(rot).as_array();
                let arr: Signature = [edges[0] as u8, edges[1] as u8, edges[2] as u8, edges[3] as u8];
                rotations[rot_idx as usize] = arr;
                for &c in &arr {
                    if c != BORDER && c > max_color {
                        max_color = c;
                    }
                }
                signature_lookup
                    .entry(arr)
                    .or_default()
                    .push((pid as u16, rot_idx));
            }
            piece_rotations.push(rotations);
        }

        let k_colors = (max_color + 1) as usize;
        let size = puzzle.width as usize;

        Self {
            puzzle,
            piece_rotations,
            signature_lookup,
            k_colors,
            size,
            n_pieces,
        }
    }

    /// Get (N, E, S, W) edges for a piece + rotation.
    pub fn piece_edges(&self, pid: u16, rot: u8) -> Signature {
        self.piece_rotations[pid as usize][rot as usize]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_puzzle_io::load_puzzle;
    use std::path::Path;

    fn data_path(rel: &str) -> std::path::PathBuf {
        // Tests run from the crate dir; data is at v2's parent's data/.
        // Try both relative paths.
        let p = std::path::PathBuf::from("../../../data/generated").join(rel);
        if p.exists() { return p; }
        let p = std::path::PathBuf::from("data/generated").join(rel);
        p
    }

    #[test]
    fn loads_small_puzzle() {
        let path = data_path("size_4_colors_6_92cd6738.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(&path).expect("load");
        let ctx = PepsContext::new(Arc::new(puzzle));
        assert_eq!(ctx.size, 4);
        assert!(ctx.k_colors >= 2);
        assert_eq!(ctx.n_pieces, 16);
    }
}
