// W1 — PEPS with Lagrangian piece-uniqueness for Eternity II.
//
// Rust port of the validated Python implementation in
// scripts/w1_peps/peps_quimb_lagrangian.py.
//
// Algorithmic reference: vault/concepts/w1-peps-design-derivation.md
// Empirical validation: vault/concepts/w1-peps-empirical-results.md
//
// This crate provides:
//   - PepsContext: holds puzzle + lookup tables for efficient tensor builds.
//   - build_cell_tensor: construct the (K,K,K,K) tensor for a given cell.
//   - boundary_mps_contract: chi-truncated boundary-MPS contraction.
//   - lagrangian_dual: iteratively enforce piece-uniqueness via Lagrangian.
//   - sequential_piece_fixing: greedy cell-by-cell fixing.
//
// The eventual goal: canonical 16×16 PEPS contraction in minutes/hours
// instead of Python's projected days.

#![forbid(unsafe_code)]

use eternity2_core::{Puzzle, Rotation, BORDER};
use std::sync::Arc;

pub mod tensor;
pub mod mps;
pub mod lagrangian;

/// Context for PEPS computations, shared across iterations.
pub struct PepsContext {
    pub puzzle: Arc<Puzzle>,
    /// piece_rotations[pid] = [(N, E, S, W); 4] for the 4 rotations
    pub piece_rotations: Vec<[[u8; 4]; 4]>,
    /// Reverse lookup: (N, E, S, W) -> list of (pid, rot)
    pub signature_lookup: std::collections::HashMap<[u8; 4], Vec<(u16, u8)>>,
    pub k_colors: usize, // K = n_interior_colors + 1 (BORDER = 0)
}

impl PepsContext {
    pub fn new(puzzle: Arc<Puzzle>) -> Self {
        let n_pieces = puzzle.pieces().len();
        let mut piece_rotations = Vec::with_capacity(n_pieces);
        let mut signature_lookup = std::collections::HashMap::new();
        let mut max_color: u8 = 0;

        for (pid, piece) in puzzle.pieces().iter().enumerate() {
            let mut rotations = [[0u8; 4]; 4];
            for rot_idx in 0..4 {
                let rot = match rot_idx {
                    0 => Rotation::R0,
                    1 => Rotation::R90,
                    2 => Rotation::R180,
                    _ => Rotation::R270,
                };
                let edges = piece.edges.rotated(rot).as_array();
                let arr: [u8; 4] = [edges[0] as u8, edges[1] as u8, edges[2] as u8, edges[3] as u8];
                rotations[rot_idx] = arr;
                for &c in &arr {
                    if c != BORDER && c > max_color {
                        max_color = c;
                    }
                }
                signature_lookup
                    .entry(arr)
                    .or_insert_with(Vec::new)
                    .push((pid as u16, rot_idx as u8));
            }
            piece_rotations.push(rotations);
        }

        // K = max interior color + 1 (for BORDER=0) + 1 (because colors are 0..max)
        // Actually our convention: BORDER=0, interior colors 1..=max_color.
        // So K = max_color + 1.
        let k_colors = (max_color + 1) as usize;

        Self {
            puzzle,
            piece_rotations,
            signature_lookup,
            k_colors,
        }
    }

    /// Get (N, E, S, W) edges for a piece + rotation, as u8 array.
    pub fn piece_edges(&self, pid: u16, rot: u8) -> [u8; 4] {
        self.piece_rotations[pid as usize][rot as usize]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_puzzle_io::load_puzzle;
    use std::path::Path;

    #[test]
    fn loads_small_puzzle() {
        let path = Path::new("../../../data/generated/size_4_colors_6_92cd6738.csv");
        if !path.exists() {
            // Try another relative path
            return; // skip if data missing
        }
        let puzzle = load_puzzle(path).expect("load");
        let ctx = PepsContext::new(Arc::new(puzzle));
        assert_eq!(ctx.puzzle.width, 4);
        // K should be at least 2 (BORDER + at least 1 interior)
        assert!(ctx.k_colors >= 2);
    }
}
