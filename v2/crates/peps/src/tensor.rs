// PEPS cell tensor construction.

use crate::{PepsContext, PieceRot};
use eternity2_core::BORDER;
use ndarray::Array4;

/// Build the full (K, K, K, K) cell tensor at position `pos`.
///
/// - `mu` is the Lagrangian shadow price per piece (length n_pieces).
/// - `pinned`: optional forced (pid, rot) for this cell.
/// - `excluded_pieces`: pieces that cannot be at this cell.
///
/// The tensor encodes:
///   T[cN, cE, cS, cW] = sum over (pid, rot) such that
///                        piece_edges(pid, rot) == (cN, cE, cS, cW)
///                        AND piece not excluded
///                        AND border-axes match (only BORDER at borders).
///                      weighted by exp(-mu[pid]).
pub fn build_cell_tensor(
    ctx: &PepsContext,
    pos: usize,
    mu: &[f64],
    pinned: Option<PieceRot>,
    excluded_pieces: &[bool],
) -> Array4<f64> {
    let k = ctx.k_colors;
    let size = ctx.size;
    let y = pos / size;
    let x = pos % size;
    let n_border = y == 0;
    let s_border = y == size - 1;
    let w_border = x == 0;
    let e_border = x == size - 1;

    let mut t = Array4::<f64>::zeros((k, k, k, k));

    let border_ok = |cn: u8, ce: u8, cs: u8, cw: u8| -> bool {
        let b = BORDER as u8;
        if n_border && cn != b { return false; }
        if e_border && ce != b { return false; }
        if s_border && cs != b { return false; }
        if w_border && cw != b { return false; }
        if !n_border && cn == b { return false; }
        if !e_border && ce == b { return false; }
        if !s_border && cs == b { return false; }
        if !w_border && cw == b { return false; }
        true
    };

    if let Some((pid_pin, rot_pin)) = pinned {
        let sig = ctx.piece_edges(pid_pin, rot_pin);
        let [cn, ce, cs, cw] = sig;
        if !border_ok(cn, ce, cs, cw) {
            return t; // invalid pin → zeroed tensor (will cause Z=0)
        }
        t[[cn as usize, ce as usize, cs as usize, cw as usize]] = (-mu[pid_pin as usize]).exp();
        return t;
    }

    for (sig, placements) in &ctx.signature_lookup {
        let [cn, ce, cs, cw] = *sig;
        if !border_ok(cn, ce, cs, cw) { continue; }
        let mut w = 0.0;
        for &(pid, _rot) in placements {
            if excluded_pieces[pid as usize] { continue; }
            w += (-mu[pid as usize]).exp();
        }
        if w > 0.0 {
            t[[cn as usize, ce as usize, cs as usize, cw as usize]] += w;
        }
    }
    t
}

/// Build all cell tensors in parallel.
pub fn build_all_cell_tensors(
    ctx: &PepsContext,
    mu: &[f64],
    pinned: &[Option<PieceRot>],
) -> Vec<Array4<f64>> {
    use rayon::prelude::*;
    let size = ctx.size;
    let n_cells = size * size;

    // Build exclusions from pinned
    let mut excluded = vec![false; ctx.n_pieces];
    for &maybe in pinned.iter() {
        if let Some((pid, _)) = maybe {
            excluded[pid as usize] = true;
        }
    }

    (0..n_cells)
        .into_par_iter()
        .map(|pos| {
            let pin = pinned[pos];
            // For the pinned cell, we DON'T want to exclude its own piece (so it can still appear)
            let local_excl = if let Some((pid, _)) = pin {
                let mut e = excluded.clone();
                e[pid as usize] = false;
                e
            } else {
                excluded.clone()
            };
            build_cell_tensor(ctx, pos, mu, pin, &local_excl)
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::PepsContext;
    use eternity2_puzzle_io::load_puzzle;
    use std::path::PathBuf;
    use std::sync::Arc;

    fn data_path(rel: &str) -> PathBuf {
        let p = PathBuf::from("../../../data/generated").join(rel);
        if p.exists() { return p; }
        PathBuf::from("data/generated").join(rel)
    }

    #[test]
    fn corner_tensor_has_only_border_compatible_entries() {
        let path = data_path("size_4_colors_6_92cd6738.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(&path).unwrap();
        let ctx = PepsContext::new(Arc::new(puzzle));
        let mu = vec![0.0; ctx.n_pieces];
        let exclusions = vec![false; ctx.n_pieces];

        let t = build_cell_tensor(&ctx, 0, &mu, None, &exclusions);
        let sum: f64 = t.iter().sum();
        assert!(sum > 0.0, "corner tensor should have non-zero entries");

        for cn in 0..ctx.k_colors {
            for ce in 0..ctx.k_colors {
                for cs in 0..ctx.k_colors {
                    for cw in 0..ctx.k_colors {
                        let v = t[[cn, ce, cs, cw]];
                        if v > 0.0 {
                            assert_eq!(cn, BORDER as usize);
                            assert_eq!(cw, BORDER as usize);
                            assert_ne!(ce, BORDER as usize);
                            assert_ne!(cs, BORDER as usize);
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn interior_tensor_has_no_border_entries() {
        // 6×6 has interior cells; use a 6×6 puzzle.
        let path = data_path("size_6_colors_6_543a4a64.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(&path).unwrap();
        let ctx = PepsContext::new(Arc::new(puzzle));
        let mu = vec![0.0; ctx.n_pieces];
        let exclusions = vec![false; ctx.n_pieces];

        // Cell (2, 2) = pos 14 in a 6×6 puzzle (interior).
        let t = build_cell_tensor(&ctx, 2 * 6 + 2, &mu, None, &exclusions);
        // Any non-zero entry must have all axes NON-BORDER.
        for cn in 0..ctx.k_colors {
            for ce in 0..ctx.k_colors {
                for cs in 0..ctx.k_colors {
                    for cw in 0..ctx.k_colors {
                        let v = t[[cn, ce, cs, cw]];
                        if v > 0.0 {
                            assert_ne!(cn, BORDER as usize);
                            assert_ne!(ce, BORDER as usize);
                            assert_ne!(cs, BORDER as usize);
                            assert_ne!(cw, BORDER as usize);
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn pinned_cell_has_single_entry() {
        let path = data_path("size_4_colors_6_92cd6738.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(&path).unwrap();
        let ctx = PepsContext::new(Arc::new(puzzle));
        let mu = vec![0.0; ctx.n_pieces];
        let exclusions = vec![false; ctx.n_pieces];

        // Pick a piece valid for the corner: scan options
        let mut chosen: Option<crate::PieceRot> = None;
        let n_border = true; let w_border = true;
        for pid in 0..ctx.n_pieces {
            for rot in 0..4u8 {
                let s = ctx.piece_edges(pid as u16, rot);
                if s[0] == BORDER as u8 && s[3] == BORDER as u8
                   && s[1] != BORDER as u8 && s[2] != BORDER as u8 {
                    chosen = Some((pid as u16, rot));
                    break;
                }
            }
            if chosen.is_some() { break; }
        }
        let _ = (n_border, w_border);

        let pin = chosen.expect("a corner piece");
        let t = build_cell_tensor(&ctx, 0, &mu, Some(pin), &exclusions);
        let nonzero = t.iter().filter(|&&v| v > 0.0).count();
        assert_eq!(nonzero, 1, "pinned cell should have exactly one non-zero entry");
    }
}
