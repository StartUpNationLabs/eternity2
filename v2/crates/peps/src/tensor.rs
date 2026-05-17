// PEPS cell tensor construction.
//
// For each cell at (y, x), build a 4-axis tensor T[cN, cE, cS, cW] where each
// axis has dim K = n_colors. The tensor encodes:
//   T[cN, cE, cS, cW] = Σ_{(pid, rot): piece(pid).rotated(rot).edges = (cN, cE, cS, cW)}
//                       exp(-μ_pid)
//   subject to: border-adjacent axes are constrained to BORDER (=0).

use crate::PepsContext;
use eternity2_core::BORDER;
use ndarray::Array4;

/// Build the full (K, K, K, K) cell tensor at position `pos`.
///
/// μ is the Lagrangian shadow price per piece.
/// pinned: Option<(pid, rot)>: if Some, cell is forced to a specific (pid, rot).
/// excluded_pieces: pieces that cannot be at this cell (e.g., pinned elsewhere).
pub fn build_cell_tensor(
    ctx: &PepsContext,
    pos: usize,
    mu: &[f64],
    pinned: Option<(u16, u8)>,
    excluded_pieces: &[bool], // excluded_pieces[pid] = true if can't use
) -> Array4<f64> {
    let k = ctx.k_colors;
    let size = ctx.puzzle.width as usize;
    let y = pos / size;
    let x = pos % size;
    let n_border = y == 0;
    let s_border = y == size - 1;
    let w_border = x == 0;
    let e_border = x == size - 1;

    let mut t = Array4::<f64>::zeros((k, k, k, k));

    if let Some((pid_pinned, rot_pinned)) = pinned {
        let sig = ctx.piece_edges(pid_pinned, rot_pinned);
        let cn = sig[0] as usize;
        let ce = sig[1] as usize;
        let cs = sig[2] as usize;
        let cw = sig[3] as usize;
        // Check border consistency
        if (n_border && cn != BORDER as usize)
            || (e_border && ce != BORDER as usize)
            || (s_border && cs != BORDER as usize)
            || (w_border && cw != BORDER as usize)
            || (!n_border && cn == BORDER as usize)
            || (!e_border && ce == BORDER as usize)
            || (!s_border && cs == BORDER as usize)
            || (!w_border && cw == BORDER as usize)
        {
            return t; // all zeros — invalid pin
        }
        t[[cn, ce, cs, cw]] = (-mu[pid_pinned as usize]).exp();
        return t;
    }

    for (sig, placements) in &ctx.signature_lookup {
        let cn = sig[0] as usize;
        let ce = sig[1] as usize;
        let cs = sig[2] as usize;
        let cw = sig[3] as usize;

        if n_border && cn != BORDER as usize { continue; }
        if e_border && ce != BORDER as usize { continue; }
        if s_border && cs != BORDER as usize { continue; }
        if w_border && cw != BORDER as usize { continue; }
        if !n_border && cn == BORDER as usize { continue; }
        if !e_border && ce == BORDER as usize { continue; }
        if !s_border && cs == BORDER as usize { continue; }
        if !w_border && cw == BORDER as usize { continue; }

        let mut w = 0.0;
        for &(pid, _rot) in placements {
            if excluded_pieces[pid as usize] {
                continue;
            }
            w += (-mu[pid as usize]).exp();
        }
        if w > 0.0 {
            t[[cn, ce, cs, cw]] += w;
        }
    }
    t
}

/// Slice border-fixed axes to BORDER=0, returning a (potentially smaller) tensor
/// view as a dynamically-shaped owned array.
///
/// Border-axis labels (returned alongside): which of N, E, S, W survive,
/// in that fixed order.
#[derive(Debug, Clone, Copy)]
pub enum Axis {
    N,
    E,
    S,
    W,
}

pub fn slice_border_axes(t: &Array4<f64>, pos: usize, size: usize) -> (ndarray::ArrayD<f64>, Vec<Axis>) {
    use ndarray::IxDyn;
    let y = pos / size;
    let x = pos % size;
    let n_border = y == 0;
    let s_border = y == size - 1;
    let w_border = x == 0;
    let e_border = x == size - 1;

    // Slice in (N, E, S, W) axis order. Surviving axes preserve order.
    let mut surviving = vec![true; 4];
    if n_border { surviving[0] = false; }
    if e_border { surviving[1] = false; }
    if s_border { surviving[2] = false; }
    if w_border { surviving[3] = false; }

    // Build the dynamic view by selecting border = 0 on those axes.
    // We use ndarray's index_axis_move or rerolled iteration. For clarity,
    // construct a fresh dyn array of the surviving shape.
    let k = t.shape()[0];
    let surv_dims: Vec<usize> = (0..4).filter(|&i| surviving[i]).map(|_| k).collect();
    let labels: Vec<Axis> = [Axis::N, Axis::E, Axis::S, Axis::W]
        .iter()
        .enumerate()
        .filter(|(i, _)| surviving[*i])
        .map(|(_, a)| *a)
        .collect();

    let mut out = ndarray::ArrayD::<f64>::zeros(IxDyn(&surv_dims));

    // Iterate over surviving indices and copy.
    let n_surv = labels.len();
    if n_surv == 0 {
        // All sliced; result is a scalar.
        let val = t[[BORDER as usize, BORDER as usize, BORDER as usize, BORDER as usize]];
        return (ndarray::arr0(val).into_dyn(), labels);
    }

    let mut idx_t = [0usize; 4];
    if !surviving[0] { idx_t[0] = BORDER as usize; }
    if !surviving[1] { idx_t[1] = BORDER as usize; }
    if !surviving[2] { idx_t[2] = BORDER as usize; }
    if !surviving[3] { idx_t[3] = BORDER as usize; }

    let mut surv_idx = vec![0usize; n_surv];
    loop {
        // Map surv_idx → idx_t for surviving axes
        let mut s = 0;
        for i in 0..4 {
            if surviving[i] {
                idx_t[i] = surv_idx[s];
                s += 1;
            }
        }
        out[IxDyn(&surv_idx)] = t[idx_t];

        // Increment surv_idx
        let mut pos = n_surv;
        loop {
            if pos == 0 { return (out, labels); }
            pos -= 1;
            surv_idx[pos] += 1;
            if surv_idx[pos] < k {
                break;
            } else {
                surv_idx[pos] = 0;
                if pos == 0 { return (out, labels); }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::PepsContext;
    use eternity2_puzzle_io::load_puzzle;
    use std::sync::Arc;
    use std::path::Path;

    #[test]
    fn build_cell_tensor_corners() {
        let path = Path::new("../../../data/generated/size_4_colors_6_92cd6738.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(path).unwrap();
        let ctx = PepsContext::new(Arc::new(puzzle));
        let n_pieces = ctx.puzzle.pieces().len();
        let mu = vec![0.0; n_pieces];
        let exclusions = vec![false; n_pieces];

        // Corner cell (0, 0)
        let t = build_cell_tensor(&ctx, 0, &mu, None, &exclusions);
        // Should have only entries at (N=BORDER, E=any non-border, S=any non-border, W=BORDER)
        // sum should be > 0
        let sum: f64 = t.sum();
        assert!(sum > 0.0, "corner tensor should be non-zero");

        // No-zero entries should be at (BORDER, e, s, BORDER)
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
}
