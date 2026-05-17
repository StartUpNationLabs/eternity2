// Boundary-MPS contraction with chi-truncation for E2 PEPS.
//
// The PEPS lives on a 2D `size × size` lattice. Each cell has a 4-axis
// tensor (cN, cE, cS, cW) of dim K each. We compute Z by absorbing the
// lattice row by row into a "boundary MPS".
//
// Boundary MPS representation: a sequence of `size` 3-axis tensors
// [bond_left, physical, bond_right], where the physical axis represents
// the "next-row N color" (= the dangling S of the last absorbed row).
//
// Algorithm:
//   1. Initial MPS: each tensor (1, K, 1) with value 1 at physical=BORDER.
//   2. For each row r, absorb that row into the MPS:
//      a. Build a "row environment" tensor for each column x:
//           E_x[bond_left, bond_right, S, cE, cW] :=
//             sum_N MPS_x[bond_left, N, bond_right] * Cell(r, x)[N, cE, S, cW]
//      b. Chain-contract the row to form a monolithic tensor with S axes per
//         column and (single) E/W axes at the row boundary (=BORDER).
//      c. SVD-truncate to bond dim chi, producing the new boundary MPS.
//   3. After the bottom row (r = size-1) where cS axes are all BORDER:
//      contract the MPS against a final "BORDER-stamp" to get scalar Z.
//
// Reference: Gray & Chan, PRX 14, 011009 (2024); validated Python in
// scripts/w1_peps/peps_quimb_lagrangian.py.

use crate::{PepsContext, PieceRot};
use crate::tensor::build_all_cell_tensors;
use eternity2_core::BORDER;
use ndarray::{Array1, Array2, Array3, Array4, Axis};
use ndarray_linalg::SVD;

/// A boundary MPS = sequence of 3-axis tensors with shape (left, K, right).
pub type Mps = Vec<Array3<f64>>;

/// Initial top boundary MPS: each cell's "N color" forced to BORDER.
fn initial_top_mps(k: usize, size: usize) -> Mps {
    (0..size)
        .map(|_| {
            let mut m = Array3::<f64>::zeros((1, k, 1));
            m[[0, BORDER as usize, 0]] = 1.0;
            m
        })
        .collect()
}

/// Absorb one row of cells (each (K, K, K, K) in NESW order) into the boundary MPS.
///
/// Algorithm:
///   For each column x: compute row_merged[x] = einsum('lnr,nesw->leswr', mps[x], cell[x])
///   Shape: (bond_left, K=E, K=S, K=W, bond_right).
///
///   Chain-contract horizontally: row_merged[x].E (axis 1) with row_merged[x+1].W (axis 3),
///   and row_merged[x].r (axis 4) with row_merged[x+1].l (axis 0).
///   Both bonds must be contracted simultaneously.
///
///   For boundary cells:
///     x=0: W is BORDER-fixed → slice W=BORDER, drop axis. Shape (l, K=E, K=S, r).
///     x=size-1: E is BORDER-fixed → slice E=BORDER, drop axis. Shape (l, K=S, K=W, r).
///
///   After chain contraction, we have a monolithic tensor with axes
///   (1, S_0, S_1, ..., S_{size-1}, 1) — all the S axes of the row.
///   SVD-truncate left-to-right to bond dim chi.
fn absorb_row(mps: &Mps, row_cells: &[Array4<f64>], chi: usize) -> Mps {
    let size = mps.len();
    assert_eq!(row_cells.len(), size, "row_cells size must match MPS size");
    let k = mps[0].shape()[1]; // physical dim = K

    // Step 1: Build row_merged[x] = (l, E, S, W, r) per cell.
    let mut row_merged: Vec<Array4<f64>> = Vec::with_capacity(size);
    for x in 0..size {
        let m = &mps[x];
        let c = &row_cells[x];
        let l_dim = m.shape()[0];
        let r_dim = m.shape()[2];
        // result shape: (l, E, S, W, r)
        // but ndarray doesn't have native 5d arrays in Array5; use ArrayD or fold dims.
        // We'll keep it as Array4 by combining left and right into a single (l*r) axis.
        // Actually it's cleaner to use Array4 with the LAST axis being the joint (l, r) bond.
        //
        // Easier: combine l and r into a single axis "lr" to keep it 4D.
        // Result shape: (l*r, K=E, K=S, K=W).
        // Wait, we need to track l and r separately because subsequent contractions tie them
        // to neighboring tensors. Let me just use ArrayD.

        // Build with manual loops; ndarray's einsum is limited.
        // We want: out[l, e, s, w, r] = sum_n m[l, n, r] * c[n, e, s, w]
        // Reshape m to (l_dim*r_dim, k): m_mat[l*r, n]
        // Reshape c to (k, k*k*k): c_mat[n, e*s*w]
        // matmul: (l*r, k) @ (k, e*s*w) = (l*r, e*s*w)
        // reshape to (l, r, e, s, w), transpose to (l, e, s, w, r).
        let m_mat = m
            .view()
            .to_shape((l_dim * r_dim, k))
            .expect("reshape mps")
            .to_owned();
        let c_mat = c
            .view()
            .to_shape((k, k * k * k))
            .expect("reshape cell")
            .to_owned();
        let product = m_mat.dot(&c_mat); // (l*r, e*s*w)
        let shaped = product
            .into_shape_with_order((l_dim, r_dim, k, k, k))
            .expect("reshape product");
        // Now transpose to (l, e, s, w, r) - axes 0=l, 1=r, 2=e, 3=s, 4=w
        // We want (0=l, 2=e, 3=s, 4=w, 1=r)
        let transposed = shaped.permuted_axes([0, 2, 3, 4, 1]);
        // Convert to ArrayBase (still 5D). We'll store as flat ArrayD for now.
        // Actually we still want 4D. Combine (l, r) into a single axis at the end?
        // No — we need to preserve l and r separately for the chain contraction.

        // Store as Array4 with shape (l*K_E, K_S, K_W, r) — no wait. Let me use
        // ArrayD to keep 5D explicit.
        // (Since Array5 doesn't exist in older ndarray.)
        // We'll keep them as ArrayD<f64> with shape [l, e, s, w, r].
        let _ = transposed;

        // For simplicity, use ArrayD everywhere here on out.
        // First, let me restructure: keep row_merged as ArrayD with shape [l, e, s, w, r].
        // The Array4 type doesn't have an Array5 sibling; use ArrayD.
        // Refactor: change Vec<Array4<f64>> to Vec<ArrayD<f64>>.
        unimplemented!("intermediate placeholder; will refactor to ArrayD below");
    }

    // Convert to ArrayD-based approach.
    // (Note: this function's signature needs to use ArrayD for the per-column
    // 5-axis tensor; the cell tensors stay 4-axis. We'll return Vec<Array3> for
    // the boundary MPS as usual.)
    unimplemented!("see absorb_row_d below");
}

// ---- ArrayD-based implementation ----
//
// Using ndarray::ArrayD for the variable-rank intermediate tensors.

use ndarray::ArrayD;
use ndarray::IxDyn;

fn absorb_row_d(mps: &Mps, row_cells: &[Array4<f64>], chi: usize) -> Mps {
    let size = mps.len();
    assert_eq!(row_cells.len(), size);
    let k = mps[0].shape()[1];

    // Step 1: row_merged[x] has shape [l, e, s, w, r].
    let mut row_merged: Vec<ArrayD<f64>> = Vec::with_capacity(size);
    for x in 0..size {
        let m = &mps[x];
        let c = &row_cells[x];
        let l_dim = m.shape()[0];
        let r_dim = m.shape()[2];

        let m_mat = m
            .view()
            .to_shape((l_dim * r_dim, k))
            .expect("reshape mps")
            .to_owned();
        let c_mat = c
            .view()
            .to_shape((k, k * k * k))
            .expect("reshape cell")
            .to_owned();
        let product = m_mat.dot(&c_mat); // (l*r, e*s*w)
        // Reshape to (l, r, e, s, w) then permute to (l, e, s, w, r).
        let shaped = product
            .into_shape_with_order((l_dim, r_dim, k, k, k))
            .expect("reshape product")
            .permuted_axes([0, 2, 3, 4, 1])
            .as_standard_layout()
            .to_owned()
            .into_dyn();
        row_merged.push(shaped);
    }

    // Step 2: Chain-contract along (E,W) and (r,l) pairs.
    //
    // Start with row_merged[0] sliced at W=BORDER (since x=0 is left border).
    //   Shape [l_0, K, K, r_0] = [1, K=E_0, K=S_0, r_0]  (after slicing W axis 3).
    // Maintain accumulator with axes:
    //   [1, S_0, S_1, ..., S_{x-1}, E_{x-1}, r_{x-1}]
    // After absorbing column x ≥ 1:
    //   [1, S_0, ..., S_x, E_x, r_x]
    // For x = size-1 (right border), slice E_{size-1}=BORDER → drop that axis.
    //
    // Final accumulator: [1, S_0, ..., S_{size-1}, 1] = `size`+2 axes.

    // Initialize: row_merged[0] sliced at W=BORDER.
    // row_merged[0] shape: [l=1, E=K, S=K, W=K, r=K-or-1].
    // We want to keep [1, E, S, r] — slice W=BORDER (axis 3, index BORDER).
    let mut accum: ArrayD<f64> = row_merged[0]
        .index_axis(Axis(3), BORDER as usize)
        .to_owned();
    // accum shape: [l, E, S, r] = 4-d

    for x in 1..size {
        let bm = &row_merged[x];
        let is_right = x == size - 1;
        // bm shape: [l_x, E_x, S_x, W_x, r_x].

        // Identify axes in accum:
        //   accum has ndim = 1 (l_0) + x (S_0..S_{x-1}) + 1 (E_{x-1}) + 1 (r_{x-1}) = x + 3
        //   so axes are: 0=l_0, 1..x=S_0..S_{x-1}, x+1=E_{x-1}, x+2=r_{x-1}
        // Need to contract: accum.E_{x-1} with bm.W_x, accum.r_{x-1} with bm.l_x.
        // After: result axes [l_0, S_0..S_{x-1}, S_x, E_x, r_x] = x+4 axes (one extra S).

        // For tractability, do this via reshape + matmul:
        //   Reshape accum to (prefix=l_0*prod(S_0..S_{x-1}), E_{x-1}, r_{x-1}).
        //   Reshape bm to (l_x, E_x*S_x*W_x*r_x).
        //   Then we want to contract E_{x-1} with W_x (3rd axis of bm) and r_{x-1} with l_x.
        //
        //   Approach: combine bm to (l_x, W_x, E_x*S_x*r_x) by reshape+transpose,
        //   so we can matmul accum_flat[prefix, E*r] with bm[E*r, S*E_x*r_x] (where
        //   E*r := the "tile" of (W*l) for cell x). Then output prefix × S × E_x × r_x.

        let prefix_dims: Vec<usize> = accum.shape()[..accum.ndim() - 2].to_vec();
        let prefix_size: usize = prefix_dims.iter().product();
        let e_prev_dim = accum.shape()[accum.ndim() - 2];
        let r_prev_dim = accum.shape()[accum.ndim() - 1];
        assert_eq!(e_prev_dim, k);
        // accum reshaped to (prefix, e_prev, r_prev) = (prefix, K, K)
        let accum_2d = accum
            .into_shape_with_order(IxDyn(&[prefix_size, e_prev_dim, r_prev_dim]))
            .expect("reshape accum");

        // bm: [l_x, E_x, S_x, W_x, r_x]. Want to contract (W_x, l_x) with (e_prev, r_prev).
        // Rearrange bm to (l_x, W_x, E_x*S_x*r_x): permute axes [0, 3, 1, 2, 4] → flatten last 3.
        let l_x = bm.shape()[0];
        let e_x = bm.shape()[1];
        let s_x = bm.shape()[2];
        let w_x = bm.shape()[3];
        let r_x = bm.shape()[4];
        assert_eq!(l_x, r_prev_dim);
        assert_eq!(w_x, e_prev_dim);
        let bm_perm = bm
            .clone()
            .into_dimensionality::<ndarray::Ix5>()
            .expect("5d view")
            .permuted_axes([0, 3, 1, 2, 4])
            .as_standard_layout()
            .to_owned();
        // shape (l_x, w_x, e_x, s_x, r_x)
        let bm_3d = bm_perm
            .into_shape_with_order((l_x, w_x, e_x * s_x * r_x))
            .expect("reshape bm");

        // Now matmul:
        //   accum_2d[prefix, e_prev=W_x, r_prev=l_x] × bm_3d[l_x, W_x, e_x*s_x*r_x]
        //   = output[prefix, e_x*s_x*r_x]
        // To do this with standard BLAS, flatten:
        //   accum_flat[prefix, l_x*W_x] (after transposing to (prefix, l_x, W_x))
        //   bm_flat[l_x*W_x, e_x*s_x*r_x]
        // Hmm I want to contract over (l_x, W_x) which appear in different orders.
        // accum_2d has (prefix, W_x, l_x) but we said (prefix, e_prev=W_x, r_prev=l_x).
        // bm_3d has (l_x, W_x, e_x*s_x*r_x).
        // Goal: sum_{l, w} accum_2d[p, w, l] * bm_3d[l, w, k] → out[p, k].
        // = (accum_2d reshaped to (p, w*l)) @ (bm_3d permuted to (w*l, k))
        // i.e. accum_2d.permute (p, w, l) ↦ flatten → (p, wl), bm_3d.permute (l, w, k) → (lw, k).
        // BUT the index order in the flatten must match. Let me unify:
        //   accum_2d (p, w, l) → flat (p, w*l) using row-major: index = w * L + l.
        //   bm_3d (l, w, k) → flat (l*w, k) where (l, w) → l * W + w.
        // We need the inner index to match: w*L + l (from accum) vs l*W + w (from bm). They don't.

        // Easier: explicitly compute via einsum-like routine using opt_einsum...
        // But we don't have opt_einsum in Rust. Use ndarray::Zip or manual reshape:
        //   Permute bm_3d (l, w, k) to (w, l, k): now flat (w, l, k) → (w*L, k).
        //   Permute accum_2d (p, w, l) to (p, w, l) → flat (p, w*L) with index w*L + l.
        // Now they match!

        let bm_3d_arr = bm_3d;
        let bm_3d_perm = bm_3d_arr
            .into_dimensionality::<ndarray::Ix3>()
            .expect("3d")
            .permuted_axes([1, 0, 2]) // (w, l, k)
            .as_standard_layout()
            .to_owned();
        let bm_flat = bm_3d_perm
            .into_shape_with_order((w_x * l_x, e_x * s_x * r_x))
            .expect("reshape bm flat");

        // accum_2d shape: (prefix_size, e_prev=W_x, r_prev=l_x).
        // Flatten to (prefix_size, W_x*l_x) row-major: index = W_x*l + W_index? Wait,
        // ndarray row-major: for shape (P, W, L), index (p, w, l) → p*W*L + w*L + l.
        // Flattening (W, L) → W*L gives index w*L + l. ✓ (matches bm_flat's w*L + l).
        let accum_flat = accum_2d
            .into_shape_with_order((prefix_size, w_x * l_x))
            .expect("reshape accum flat");

        // matmul
        let product_2d: Array2<f64> = accum_flat
            .into_dimensionality::<ndarray::Ix2>()
            .expect("2d accum")
            .dot(&bm_flat
                .into_dimensionality::<ndarray::Ix2>()
                .expect("2d bm"));

        // product_2d shape: (prefix_size, e_x*s_x*r_x)
        // Reshape to (prefix..., e_x, s_x, r_x).
        // But wait — we want the new accum to have axes [l_0, S_0, ..., S_{x-1}, S_x, E_x, r_x].
        // Currently we have prefix = (l_0, S_0, ..., S_{x-1}), and the matmul output adds
        // (e_x, s_x, r_x) at the end. We need to REORDER to put S_x BEFORE E_x.
        // Specifically: split last axis to (e_x, s_x, r_x), permute to (s_x, e_x, r_x).

        let mut new_shape: Vec<usize> = prefix_dims.iter().copied().collect();
        new_shape.extend([e_x, s_x, r_x]);
        let product_unsh = product_2d
            .into_shape_with_order(IxDyn(&new_shape))
            .expect("reshape product");

        // Permute: move s_x (axis len-2) to BEFORE e_x (axis len-3).
        // Current axes: [0..prefix.len(), e_x, s_x, r_x] = [0..len, len, len+1, len+2]
        // Want: [0..prefix.len(), s_x, e_x, r_x] = swap axes len and len+1.
        let n_prefix = prefix_dims.len();
        let mut perm: Vec<usize> = (0..product_unsh.ndim()).collect();
        // Swap perm[n_prefix] (=e_x) and perm[n_prefix+1] (=s_x)
        perm.swap(n_prefix, n_prefix + 1);
        accum = product_unsh.permuted_axes(perm).as_standard_layout().to_owned();

        // For x = size-1 (right border): slice E_x = BORDER (which is the second-to-last axis now).
        if is_right {
            // accum axes: [..., S_x, E_x, r_x]. Slice E_x at index BORDER.
            // E_x is at axis (ndim - 2).
            let e_axis = accum.ndim() - 2;
            accum = accum.index_axis(Axis(e_axis), BORDER as usize).to_owned();
        }
    }

    // Now accum should have shape (1, S_0, S_1, ..., S_{size-1}, 1) — i.e., size+2 axes.
    // SVD-decompose left-to-right into MPS with bond ≤ chi.
    assert_eq!(accum.ndim(), size + 2,
        "accum ndim {} expected {}", accum.ndim(), size + 2);
    assert_eq!(accum.shape()[0], 1, "left boundary should be 1");
    assert_eq!(accum.shape()[accum.ndim() - 1], 1, "right boundary should be 1");

    // Decompose accum (shape (1, K, K, ..., K, 1)) into MPS via SVD sweep.
    // Reshape to 2D (1*K, K^{size-1} * 1) for first SVD, then slide.
    let mut new_mps: Mps = Vec::with_capacity(size);
    let mut leftover = accum;
    let mut bond_left = 1usize;
    for col in 0..size {
        // leftover has shape (bond_left, K, K, ..., K, 1).
        // First drop the trailing 1 if at the last column:
        let shape_now = leftover.shape().to_vec();
        // We want to split off the next physical (K-dim) axis.
        // Current leftover after each step: shape (bond_left, K^remaining, 1).
        // Specifically, on entry to col=c: shape is (bond_left, K, K^(size-1-c), 1)
        // — c physical axes already split off.
        // But we always reshape to (bond_left * K, rest) for SVD.
        let _ = shape_now;
        let n_remaining_phys = leftover.ndim() - 2; // minus bond_left and trailing 1
        // Compute "rest" = K^(n_remaining_phys - 1) * 1
        let rest_dim: usize = leftover.shape()[2..].iter().product();
        let total_size: usize = leftover.len();
        let _ = total_size;

        // Reshape leftover to (bond_left * K, rest_dim).
        let m_mat = leftover
            .into_shape_with_order((bond_left * k, rest_dim))
            .expect("reshape leftover for SVD");

        // SVD
        let m_owned: Array2<f64> = m_mat.into_dimensionality::<ndarray::Ix2>().expect("2d");
        let (u_opt, s_vec, vt_opt) = m_owned.svd(true, true).expect("svd");
        let u = u_opt.expect("u");
        let vt = vt_opt.expect("vt");

        // Truncate to chi
        let keep = chi.min(s_vec.len());
        let u_kept: Array2<f64> = u.slice(ndarray::s![.., ..keep]).to_owned();
        let s_kept: Array1<f64> = s_vec.slice(ndarray::s![..keep]).to_owned();
        let vt_kept: Array2<f64> = vt.slice(ndarray::s![..keep, ..]).to_owned();

        // mps_col = u_kept reshaped to (bond_left, K, keep)
        let mps_col: Array3<f64> = u_kept
            .into_shape_with_order((bond_left, k, keep))
            .expect("reshape u to 3d")
            .into_dimensionality::<ndarray::Ix3>()
            .expect("3d");
        new_mps.push(mps_col);

        // S * Vt becomes the new leftover, reshaped from (keep, rest_dim) back to
        // (keep, K, K, ..., K, 1) for the next SVD.
        let mut s_vt = vt_kept;
        for i in 0..keep {
            let scale = s_kept[i];
            let mut row = s_vt.row_mut(i);
            row.mapv_inplace(|v| v * scale);
        }
        // s_vt shape: (keep, rest_dim). Reshape to (keep, K, K, ..., K, 1) — n_remaining_phys-1 K's + trailing 1.
        let mut next_shape: Vec<usize> = vec![keep];
        for _ in 0..(n_remaining_phys - 1) {
            next_shape.push(k);
        }
        next_shape.push(1);
        if col == size - 1 {
            // After splitting the LAST physical, s_vt should be shape (keep, 1).
            // We've already absorbed the bottom 1. The final scalar factor (a 1×1 matrix)
            // gets multiplied into the last MPS tensor.
            // s_vt is (keep, 1). The last mps tensor has shape (bond_left, K, keep).
            // We want to fold the residual into it: new_mps[-1] *= s_vt.t() along right axis.
            let factor: Array1<f64> = s_vt.into_shape_with_order(keep).expect("reshape").to_owned()
                .into_dimensionality::<ndarray::Ix1>().expect("1d");
            // Multiply mps_col along its right bond axis.
            let last_idx = new_mps.len() - 1;
            let mut last = std::mem::take(&mut new_mps[last_idx]);
            let l_d = last.shape()[0];
            let p_d = last.shape()[1];
            let r_d = last.shape()[2];
            assert_eq!(r_d, keep);
            for li in 0..l_d {
                for pi in 0..p_d {
                    for ri in 0..r_d {
                        last[[li, pi, ri]] *= factor[ri];
                    }
                }
            }
            new_mps[last_idx] = last;
            break;
        }
        leftover = s_vt
            .into_shape_with_order(IxDyn(&next_shape))
            .expect("reshape leftover");
        bond_left = keep;
    }

    new_mps
}

/// Absorb the bottom row (cS axes all BORDER) → scalar Z.
///
/// Each bottom cell has its S axis forced to BORDER. So row_cells[x] for the
/// bottom row has the structure: T[N, E, S=BORDER, W]. We contract this with
/// the boundary MPS (where physical = N) and sum out everything → scalar.
fn absorb_bottom_row(mps: &Mps, row_cells: &[Array4<f64>]) -> f64 {
    let size = mps.len();
    assert_eq!(row_cells.len(), size);
    let k = mps[0].shape()[1];

    // Step 1: contract each MPS tensor with the bottom cell at its column.
    //   result[x] = einsum('lnr,nesw->leswr', mps[x], cell[x])
    //   Then slice s = BORDER.
    //   Result shape: (l, K=E, K=W, r) — 4 axes.
    let mut row_merged: Vec<ArrayD<f64>> = Vec::with_capacity(size);
    for x in 0..size {
        let m = &mps[x];
        let c = &row_cells[x];
        let l_dim = m.shape()[0];
        let r_dim = m.shape()[2];
        let m_mat = m
            .view()
            .to_shape((l_dim * r_dim, k))
            .expect("reshape mps")
            .to_owned();
        let c_mat = c
            .view()
            .to_shape((k, k * k * k))
            .expect("reshape cell")
            .to_owned();
        let product = m_mat.dot(&c_mat); // (l*r, e*s*w)
        // shape (l, r, e, s, w), permute to (l, e, s, w, r)
        let shaped = product
            .into_shape_with_order((l_dim, r_dim, k, k, k))
            .expect("reshape product")
            .permuted_axes([0, 2, 3, 4, 1])
            .as_standard_layout()
            .to_owned()
            .into_dyn();
        // Slice s axis (axis 2) at BORDER.
        let sliced = shaped.index_axis(Axis(2), BORDER as usize).to_owned();
        // shape (l, e, w, r) = 4-d ArrayD
        row_merged.push(sliced);
    }

    // Step 2: chain-contract similar to absorb_row but accumulate to scalar.
    // Initial: row_merged[0] sliced at W=BORDER → (l=1, E, r).
    // Then absorb each subsequent column.
    let mut accum: ArrayD<f64> = row_merged[0]
        .index_axis(Axis(2), BORDER as usize) // W is axis 2 after S-slicing
        .to_owned(); // shape (l, E, r) = (1, K, r_0)

    for x in 1..size {
        let bm = &row_merged[x];
        let is_right = x == size - 1;
        // bm shape: (l_x, E_x, W_x, r_x).
        // accum shape so far: (l_0, E_{x-1}, r_{x-1}) for some chain.
        // Wait: there's no S accumulating since the bottom row gives scalar.
        // Let me reconsider. After absorb of column 0 (with W=BORDER), we have (l=1, E_0, r_0).
        // For column 1: contract accum.E (=E_0=W_1) and accum.r (=l_1).
        // Result: (l_0=1, E_1, r_1).
        // For column x in middle: maintained as (l_0=1, E_{x-1}, r_{x-1}).

        let prefix_size: usize = accum.shape()[..accum.ndim() - 2].iter().product();
        let e_prev = accum.shape()[accum.ndim() - 2];
        let r_prev = accum.shape()[accum.ndim() - 1];
        assert_eq!(e_prev, k);

        let l_x = bm.shape()[0];
        let e_x = bm.shape()[1];
        let w_x = bm.shape()[2];
        let r_x = bm.shape()[3];
        assert_eq!(l_x, r_prev);
        assert_eq!(w_x, e_prev);

        // bm shape (l_x, e_x, w_x, r_x). We want to contract (l_x, w_x) with (r_prev, e_prev).
        // Permute bm to (w_x, l_x, e_x, r_x), flatten to (w_x*l_x, e_x*r_x).
        let bm_perm = bm
            .clone()
            .into_dimensionality::<ndarray::Ix4>()
            .expect("4d")
            .permuted_axes([2, 0, 1, 3])
            .as_standard_layout()
            .to_owned();
        let bm_flat = bm_perm
            .into_shape_with_order((w_x * l_x, e_x * r_x))
            .expect("bm flat");

        // accum (prefix, e_prev=W_x, r_prev=l_x) flatten to (prefix, W_x*l_x) — same indexing convention.
        let accum_flat = accum
            .into_shape_with_order((prefix_size, e_prev * r_prev))
            .expect("accum flat");

        let product_2d = accum_flat
            .into_dimensionality::<ndarray::Ix2>()
            .expect("2d accum")
            .dot(&bm_flat
                .into_dimensionality::<ndarray::Ix2>()
                .expect("2d bm"));

        // product_2d shape (prefix, e_x*r_x). Reshape to (prefix, e_x, r_x).
        let mut new_shape = vec![prefix_size, e_x, r_x];
        accum = product_2d
            .into_shape_with_order(IxDyn(&new_shape))
            .expect("reshape product");

        if is_right {
            // Slice E_x = BORDER. accum shape is (prefix, e_x, r_x); E axis is axis 1.
            accum = accum.index_axis(Axis(1), BORDER as usize).to_owned();
            // Now (prefix, r_x); r_x should be 1 (right boundary of MPS).
        }
    }

    // accum should be a scalar (all axes collapsed or size 1).
    // For size=1 puzzles or when fully reduced, accum is 0-d or all-1 shape.
    let z: f64 = accum.iter().sum();
    z
}

/// Compute log Z by chi-truncated boundary-MPS contraction.
pub fn log_z(
    ctx: &PepsContext,
    cells: &[Array4<f64>],
    chi: usize,
) -> f64 {
    let size = ctx.size;
    let k = ctx.k_colors;
    let mut mps = initial_top_mps(k, size);
    for r in 0..size - 1 {
        let row: Vec<Array4<f64>> = (0..size).map(|x| cells[r * size + x].clone()).collect();
        mps = absorb_row_d(&mps, &row, chi);
    }
    let bottom: Vec<Array4<f64>> = (0..size)
        .map(|x| cells[(size - 1) * size + x].clone())
        .collect();
    let z = absorb_bottom_row(&mps, &bottom);
    if z <= 0.0 {
        f64::NEG_INFINITY
    } else {
        z.ln()
    }
}

/// Compute log Z given mu and pinned cells (high-level).
pub fn log_z_lagrangian(
    ctx: &PepsContext,
    mu: &[f64],
    pinned: &[Option<PieceRot>],
    chi: usize,
) -> f64 {
    let cells = build_all_cell_tensors(ctx, mu, pinned);
    log_z(ctx, &cells, chi)
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_puzzle_io::load_puzzle;
    use std::path::PathBuf;
    use std::sync::Arc;

    fn data_path(rel: &str) -> PathBuf {
        let p = PathBuf::from("../../../data/generated").join(rel);
        if p.exists() { return p; }
        PathBuf::from("data/generated").join(rel)
    }

    #[test]
    fn log_z_4x4_matches_python() {
        let path = data_path("size_4_colors_6_92cd6738.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(&path).unwrap();
        let ctx = PepsContext::new(Arc::new(puzzle));
        let n_pieces = ctx.n_pieces;
        let mu = vec![0.0; n_pieces];
        let pinned: Vec<Option<PieceRot>> = vec![None; ctx.size * ctx.size];

        // Python value at mu=0, chi=64: log_Z = 5.9135
        let log_z_val = log_z_lagrangian(&ctx, &mu, &pinned, 64);
        eprintln!("log_z (4×4, chi=64) = {}", log_z_val);
        assert!((log_z_val - 5.9135).abs() < 0.01, "log_z mismatch: {} vs 5.9135", log_z_val);
    }
}
