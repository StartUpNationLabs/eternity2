// Boundary-MPS contraction with chi-truncation for E2 PEPS.
//
// CLEAN REWRITE v3: just do EXACT contraction (no chi truncation).
//
// The boundary state is a single ArrayD<f64> with shape (1, K, K, ..., K, 1)
// — `size` middle K-axes (one per column), representing the S color of the
// last absorbed row.
//
// Cost: K^size entries per row absorption. For K=8, size=8: 16M — fine.
//       For K=23, size=16: 4e21 — needs chi truncation (future work).
//
// Algorithm:
//   For each row r:
//     For each column x in 0..size:
//       Cell C(r, x) has axes (N, E, S, W) = (K, K, K, K).
//       Combine with the boundary state's x-th axis (= N for cell at (r, x)).
//       Then the new boundary's x-th axis is S.
//       Horizontal bonds E_x = W_{x+1} are contracted as we go.
//
// This is equivalent to a row-by-row sweep with horizontal chain in each row,
// implemented as a single ArrayD with stable axis order.

use crate::{PepsContext, PieceRot};
use crate::tensor::build_all_cell_tensors;
use eternity2_core::BORDER;
use ndarray::{Array1, Array2, Array4, ArrayD, Axis, IxDyn};

/// Boundary state ArrayD with shape (1, K, K, ..., K, 1) — `size`+2 axes total.
pub type BoundaryState = ArrayD<f64>;

/// Initial state: N = BORDER for all columns. Shape (1, K, K, ..., K, 1).
fn initial_state(k: usize, size: usize) -> BoundaryState {
    let mut shape: Vec<usize> = vec![1];
    for _ in 0..size {
        shape.push(k);
    }
    shape.push(1);
    let mut state = ArrayD::<f64>::zeros(IxDyn(&shape));
    let mut idx: Vec<usize> = vec![0];
    for _ in 0..size {
        idx.push(BORDER as usize);
    }
    idx.push(0);
    state[IxDyn(&idx)] = 1.0;
    state
}

/// Absorb one row into the boundary state. Returns the new boundary state.
///
/// The row has `size` cells; each cell at column x has 4-axis tensor (N, E, S, W).
/// We process columns 0..size left-to-right, contracting:
///   - boundary state's x-th N-axis with cell x's N
///   - cell x's W-axis with cell (x-1)'s E (for x > 0); for x = 0, W = BORDER
///   - cell (size-1)'s E = BORDER
///
/// After processing all columns, the new state has S of row r as the K-axes.
fn absorb_row(state: BoundaryState, row_cells: &[Array4<f64>]) -> BoundaryState {
    let size = row_cells.len();
    let k = row_cells[0].shape()[0];

    // We process column by column.
    // Maintain a "current state" ArrayD with axes:
    //   axis 0: leading 1
    //   axis 1..=size-1: middle K axes for columns we haven't yet processed
    //   axis size: <special> horizontal bond from the last processed cell (or BORDER for x=0)
    //   axis size+1: trailing 1
    //
    // Wait, this is the same complexity as before. Let me think again.
    //
    // Simpler model: maintain a single ArrayD with axes
    //   [1, S_0, S_1, ..., S_{size-1}, 1]  (the OUTPUT — the new state's S axes)
    //   plus a "running bond" axis representing the cumulative horizontal bond.
    //
    // Even better: do the row absorption in TWO passes:
    //   Pass 1: build a `row_tensor` representing the whole row as a single
    //           tensor T_row[N_0, S_0, N_1, S_1, ..., N_{size-1}, S_{size-1}, W=BORDER, E=BORDER]
    //           = sum over (e_0, ..., e_{size-2}) [horizontal bond values]
    //                of prod_x Cell(r, x)[N_x, e_x, S_x, e_{x-1}]
    //           (with e_{-1}=BORDER, e_{size-1}=BORDER)
    //   Pass 2: contract each N_x with the old state's S_x.
    //
    // Pass 1 builds row_tensor sequentially: start with cell 0 (sliced at W=BORDER),
    // chain-contract with cell 1, ..., cell size-1 (sliced at E=BORDER).
    //
    // Pass 1 cost: K^(2*size) intermediate at worst. For size=8, K=8: 8^16 ≈ 3e14 too big.
    //
    // Compromise: combine pass 1 and pass 2 into ONE row sweep that interleaves
    // horizontal absorption with vertical absorption.
    //
    // Algorithm (cleaner):
    //   For each column x in 0..size:
    //     Maintain a "running tensor" T_x with axes (1, S_0..S_{x-1}, h_{x-1}, N_x..N_{size-1}, 1)
    //     where h_{x-1} is the horizontal bond from cell x-1 (or BORDER if x=0).
    //     Absorb cell x: contract h_{x-1} (=W of cell x) and N_x with cell x's W and N axes.
    //     Result: T_{x+1} has axes (1, S_0..S_x, h_x, N_{x+1}..N_{size-1}, 1).
    //
    //   After processing all columns: T_size has axes (1, S_0..S_{size-1}, h_{size-1}, 1).
    //   Slice h_{size-1} = BORDER → final state with axes (1, S_0..S_{size-1}, 1). ✓
    //
    // The running tensor's max ndim is 1 + size + 1 + 1 = size+3 axes.
    // Max size = K^size dimensions for the (S + h + N) part.
    // K=8, size=8: K^8 = 16M. Manageable.
    // K=8, size=12: 12^8 = ouch. Actually still 8^12 = 6.8 billion. Borderline.

    // Initialize running tensor T_0 = state (shape (1, K, K, ..., K, 1)) plus
    // we need to add a "horizontal bond" axis. Initially h = BORDER (left border).
    // We can insert it before the N axes start changing: add a singleton at position
    // 1 (after leading 1) and slice it later, OR start with h merged into the
    // initial state at axis 1.
    //
    // Approach: just augment state by inserting a "h axis" of size K, fixed at BORDER.
    // We do this implicitly: when we absorb cell 0 (column 0), its W axis = BORDER
    // is the initial "h" we slice at.
    //
    // Concretely: the loop processes cells, and the running tensor's axes evolve:
    //   x=0: T has axes (1, N_0, N_1, ..., N_{size-1}, 1). Same as input state.
    //        (No h axis yet; we slice cell 0's W = BORDER directly.)
    //   After absorbing cell 0: T has axes (1, S_0, h_0, N_1, ..., N_{size-1}, 1).
    //        (Cell 0's S axis replaces N_0; cell 0's E becomes h_0.)
    //   x=1: absorb cell 1 by contracting h_0 (= cell 1's W) and N_1 (= cell 1's N).
    //        Cell 1's S and E become S_1 and h_1.
    //   ...
    //   x=size-1: absorb final cell. h_{size-1} = E of last cell = BORDER, so slice.
    //   Final T has axes (1, S_0, S_1, ..., S_{size-1}, 1). ✓

    // We implement this with explicit ArrayD reshaping.

    let mut t = state;  // current running tensor

    for x in 0..size {
        let cell = &row_cells[x];
        let is_last = x == size - 1;

        // CASE: x = 0 (left border).
        //   T axes: (1, N_0, N_1, ..., N_{size-1}, 1) → ndim = size + 2
        //   Cell axes: (N, E, S, W) = (K, K, K, K). Slice W = BORDER: (N, E, S).
        //   Contract N_0 of T (axis 1) with N of cell (axis 0).
        //   Result: T has axes (1, [E_0, S_0], N_1, ..., N_{size-1}, 1) where [E_0, S_0]
        //   replace N_0. Order: insert (S_0, h_0=E_0) at position 1 (S_0 first, h_0 after).
        //
        // CASE: 0 < x < size-1 (middle).
        //   T axes: (1, S_0, ..., S_{x-1}, h_{x-1}, N_x, N_{x+1}, ..., N_{size-1}, 1).
        //   Cell axes: (N, E, S, W) = (K, K, K, K).
        //   Contract h_{x-1} of T (axis x+1) with W of cell (axis 3),
        //   AND N_x of T (axis x+2) with N of cell (axis 0).
        //   Result: T has axes (1, S_0, ..., S_x, h_x, N_{x+1}, ..., N_{size-1}, 1) where
        //   (S_x, h_x) replace (h_{x-1}, N_x).
        //
        // CASE: x = size-1 (right border).
        //   T axes: (1, S_0, ..., S_{size-2}, h_{size-2}, N_{size-1}, 1) → ndim = size + 2
        //   Cell axes: (N, E, S, W). Slice E = BORDER: (N, S, W).
        //   Contract h_{size-2} (axis size-1) with W (axis 2),
        //   AND N_{size-1} (axis size) with N (axis 0).
        //   Result: T has axes (1, S_0, ..., S_{size-1}, 1).

        if x == 0 {
            // Slice cell W (axis 3) at BORDER. Result shape: (N, E, S).
            let cell_sliced = cell.index_axis(Axis(3), BORDER as usize).to_owned();
            // cell_sliced has shape (K, K, K) over (N, E, S).
            //
            // T has shape (1, K, K, ..., K, 1) with size middle K-axes (over N_0..N_{size-1}).
            // We want to contract T's axis-1 (N_0) with cell_sliced's axis-0 (N).
            // Result should have T's other axes plus cell_sliced's (E, S) replacing N_0.
            // Order: we want (1, S_0, h_0=E_0, N_1, N_2, ..., N_{size-1}, 1).
            //
            // Use Einstein-style contraction:
            //   T[a, N_0, N_1, ..., N_{size-1}, b] * cell_sliced[N_0, E_0, S_0] →
            //     result[a, S_0, E_0, N_1, ..., N_{size-1}, b]
            //
            // We do this via reshape + matmul:
            //   T flattened to (prefix_dim=1, N_0=K, suffix_dim = K^{size-1} * 1)
            //   cell_sliced flattened to (N_0=K, E*S=K*K)
            //   product = T_left × cell_sliced → (1 * K * suffix_dim, K * K) wait no.
            //
            // We have T[a, N_0, rest, b] where rest is shape (K, ..., K) over N_1..N_{size-1}.
            // Permute to put N_0 first: not needed since it's already axis 1.
            // Reshape T to (1, K, suffix * 1) where suffix = K^(size-1).
            // cell_sliced as (K, K*K).
            //
            // We want: out[a=1, suffix, E, S] = sum_{N_0} T[a, N_0, suffix, b] * cell_sliced[N_0, E*S]
            // After: reshape to (a, suffix, E, S) → (1, K^(size-1), K, K).
            // We then need axes (a, S, E, suffix, b) = (1, K, K, K^(size-1), 1).
            // Then split suffix back to (N_1, ..., N_{size-1}).

            let suffix_dim: usize = {
                let mut s = 1;
                for ax in 2..t.ndim() - 1 {
                    s *= t.shape()[ax];
                }
                s
            };
            assert_eq!(t.shape()[0], 1);
            assert_eq!(t.shape()[1], k);

            // Reshape T to (K, suffix_dim) — drop the leading and trailing 1.
            // axis 1 is N_0, axes 2..ndim-2 are the suffix, axis ndim-1 is trailing 1.
            let t_2d: Array2<f64> = t
                .clone()
                .into_shape_with_order((k, suffix_dim))
                .expect("reshape T")
                .into_dimensionality::<ndarray::Ix2>()
                .expect("2d");

            // cell_sliced as (K, K * K) where K = E*S unrolled with stride E*K + S.
            let cell_2d: Array2<f64> = cell_sliced
                .into_shape_with_order((k, k * k))
                .expect("reshape cell")
                .into_dimensionality::<ndarray::Ix2>()
                .expect("2d");

            // We want out[suffix, E, S] = sum_N T[N, suffix] * cell[N, E*S]
            // = (T.T @ cell)[suffix, E*S]
            let out_2d = t_2d.t().dot(&cell_2d);  // shape (suffix_dim, K*K)
            // Reshape to (suffix..., E, S) where suffix is the original size-1 K-axes.
            // Then permute (suffix, E, S) → (S, E, suffix). Then prepend a=1, append b=1.

            // For ergonomics, build the final shape directly:
            //   (1, S, E, N_1, N_2, ..., N_{size-1}, 1) → ndim = size + 3
            // axes:  [0=a=1, 1=S, 2=E=h, 3..=size+1=N_1..N_{size-1}, size+2=1]
            //
            // out_2d shape (suffix_dim, K*K) where suffix_dim = K^(size-1).
            // Reshape to (suffix..., E, S) by reshape ((K, K, ..., K, K, K), order):
            //   axes: N_1, N_2, ..., N_{size-1}, E, S
            // Then permute to (S, E, N_1, ..., N_{size-1}).

            let mut suffix_shape: Vec<usize> = Vec::new();
            for ax in 2..t.ndim() - 1 {
                suffix_shape.push(t.shape()[ax]);
            }
            suffix_shape.push(k); // E
            suffix_shape.push(k); // S
            let unshaped = out_2d
                .into_shape_with_order(IxDyn(&suffix_shape))
                .expect("reshape out");
            // unshaped axes: (N_1, ..., N_{size-1}, E, S) → ndim = size-1 + 2 = size+1
            // We want (S, E, N_1, ..., N_{size-1}). Permutation:
            //   new_axis_0 = unshaped_axis_size (=S)
            //   new_axis_1 = unshaped_axis_size-1 (=E)
            //   new_axis_2 = unshaped_axis_0 (=N_1)
            //   new_axis_3 = unshaped_axis_1 (=N_2)
            //   ...
            //   new_axis_{size-1} = unshaped_axis_{size-3} (=N_{size-1})
            let mut perm: Vec<usize> = vec![unshaped.ndim() - 1, unshaped.ndim() - 2];
            for ax in 0..unshaped.ndim() - 2 {
                perm.push(ax);
            }
            let permuted = unshaped.permuted_axes(perm);
            let permuted_std = permuted.as_standard_layout().to_owned();

            // Add leading 1 and trailing 1 axes.
            let mut new_shape: Vec<usize> = vec![1];
            new_shape.extend(permuted_std.shape().iter().copied());
            new_shape.push(1);
            t = permuted_std
                .into_shape_with_order(IxDyn(&new_shape))
                .expect("reshape final");
        } else if !is_last {
            // Middle case: 0 < x < size - 1.
            // T has axes (1, S_0, ..., S_{x-1}, h_{x-1}, N_x, N_{x+1}, ..., N_{size-1}, 1).
            // Cell has axes (N, E, S, W).
            // Contract h_{x-1} (T axis x+1) with W (cell axis 3), AND
            //          N_x (T axis x+2) with N (cell axis 0).
            // Result: T_new has axes (1, S_0, ..., S_x, h_x, N_{x+1}, ..., N_{size-1}, 1).

            // Plan: reshape T so that axes (h_{x-1}, N_x) are at the END:
            //   T flat: (prefix=K^x*1, h*N=K*K, suffix=K^{size-1-x}*1)
            // Cell flat: (N*W, E*S) = (K*K, K*K)
            // Want: out[prefix, suffix, E, S] = sum_{h, N} T[prefix, h*K+N, suffix] * cell[N*K+W=N*K+h, E*K+S]
            // We need flat-index match: T's (h, N) → h*K+N. Cell's (N, W) → N*K+W. With h=W, the inner index
            // of T is N and the inner index of cell is W=h. So they don't directly match.
            //
            // FIX: flip T's flat ordering: use (N, h) → N*K+h so it matches cell's (N, W).
            // But that requires permuting T to put N before h.

            let prefix_len = x + 1; // axes 0..=x (= leading 1 + S_0..S_{x-1})
            let h_axis = x + 1;
            let n_axis = x + 2;
            // We want axes order (..., N_x, h_{x-1}, ...).
            let mut perm: Vec<usize> = (0..t.ndim()).collect();
            perm.swap(h_axis, n_axis);  // Now (..., N_x, h_{x-1}, ...).

            let t_perm = t.clone().permuted_axes(perm);
            let t_perm_std = t_perm.as_standard_layout().to_owned();

            let prefix_dim: usize = t_perm_std.shape()[..h_axis].iter().product();
            let suffix_dim: usize = t_perm_std.shape()[n_axis + 1..].iter().product();
            assert_eq!(t_perm_std.shape()[h_axis], k);  // N axis
            assert_eq!(t_perm_std.shape()[n_axis], k);  // h axis

            // Now T_perm flat: (prefix, K, K, suffix) where middle is (N, h).
            // Reshape to (prefix, K*K, suffix).
            let t_3d: ndarray::Array3<f64> = t_perm_std
                .into_shape_with_order((prefix_dim, k * k, suffix_dim))
                .expect("reshape T")
                .into_dimensionality::<ndarray::Ix3>()
                .expect("3d");

            // Cell: (N, E, S, W) → (N*W, E*S) = (K*K, K*K) with N as outer, W as inner.
            // We want flat (N*K+W) and (E*K+S).
            let cell_2d: Array2<f64> = cell
                .clone()
                .permuted_axes([0, 3, 1, 2])  // (N, W, E, S)
                .as_standard_layout()
                .to_owned()
                .into_shape_with_order((k * k, k * k))
                .expect("reshape cell")
                .into_dimensionality::<ndarray::Ix2>()
                .expect("2d");

            // Contract: out[prefix, suffix, E*S] = sum_{N, W} T[prefix, N*K+W, suffix] * cell[N*K+W, E*S]
            // = T_3d (prefix, K*K, suffix) × cell_2d (K*K, K*K)
            // First reshape T_3d to (prefix*suffix, K*K) — move the contracting axis to one side.
            //
            // We want output (prefix, suffix, E*S). Use:
            //   T_3d permuted (prefix, suffix, K*K) → flatten (prefix*suffix, K*K)
            //   product = (prefix*suffix, K*K) @ (K*K, K*K) = (prefix*suffix, K*K) → reshape (prefix, suffix, E*S)
            let t_3d_perm = t_3d
                .permuted_axes([0, 2, 1])  // (prefix, suffix, K*K)
                .as_standard_layout()
                .to_owned();
            let t_2d_flat: Array2<f64> = t_3d_perm
                .into_shape_with_order((prefix_dim * suffix_dim, k * k))
                .expect("reshape T flat")
                .into_dimensionality::<ndarray::Ix2>()
                .expect("2d");
            let product_2d = t_2d_flat.dot(&cell_2d);  // (prefix*suffix, K*K)
            // Reshape to (prefix, suffix, E, S).
            let unshaped = product_2d
                .into_shape_with_order(IxDyn(&[prefix_dim, suffix_dim, k, k]))
                .expect("reshape product");
            // We want final axes (1, S_0, ..., S_{x-1}, S_x, h_x, N_{x+1}, ..., N_{size-1}, 1)
            // unshaped axes: 0=prefix (which carries 1*S_0*...*S_{x-1}), 1=suffix (N_{x+1}*...*N_{size-1}*1), 2=E=h_x, 3=S=S_x
            // We need: prefix unrolled to (1, S_0, ..., S_{x-1}), then S, then E, then suffix unrolled to (N_{x+1}, ..., N_{size-1}, 1).
            // Then prefix dims are [1, S_0..S_{x-1}] = [1, K, ..., K] (x dims). After prefix come (S, E), then suffix dims [N_{x+1}, ..., N_{size-1}, 1] = [K, ..., K, 1] (size-1-x dims + 1 trailing 1).

            // Reshape unshaped → (1, K, ..., K, K, K, K, ..., K, 1) with structure:
            // [1, S_0..S_{x-1}, S_x, h_x, N_{x+1}..N_{size-1}, 1]
            let mut full_shape: Vec<usize> = vec![1];
            for _ in 0..x {
                full_shape.push(k);  // S_0..S_{x-1}
            }
            full_shape.push(k); // S_x
            full_shape.push(k); // h_x
            for _ in (x + 1)..size {
                full_shape.push(k);  // N_{x+1}..N_{size-1}
            }
            full_shape.push(1);

            // We need to permute unshaped (prefix, suffix, E, S) to (prefix, S, E, suffix).
            let unshaped_perm = unshaped.permuted_axes(IxDyn(&[0, 3, 2, 1]));  // (prefix, S, E, suffix)
            let unshaped_perm_std = unshaped_perm.as_standard_layout().to_owned();
            t = unshaped_perm_std
                .into_shape_with_order(IxDyn(&full_shape))
                .expect("reshape final mid");
        } else {
            // x == size - 1, right border.
            // T has axes (1, S_0, ..., S_{size-2}, h_{size-2}, N_{size-1}, 1).
            // Cell: slice E = BORDER (axis 1) → (N, S, W) shape (K, K, K).
            // Contract h_{size-2} (T axis size-1) with W (cell axis 2),
            //          N_{size-1} (T axis size) with N (cell axis 0).
            // Result: T has axes (1, S_0, ..., S_{size-1}, 1).

            let cell_sliced = cell.index_axis(Axis(1), BORDER as usize).to_owned();
            // (N, S, W) shape (K, K, K).
            // We want flat (N, W) → N*K+W matching T's (N, h_{size-2}) ordering.

            // T axes: (1, S_0, S_1, ..., S_{size-2}, h_{size-2}, N_{size-1}, 1).
            // That's 1 + (size-1) S's + 1 h + 1 N + 1 = size + 2 axes.
            // h is at axis `size`, N is at axis `size + 1`.
            // BUT after x=0 (for size=2, no middle iterations), ndim = size + 3 = 5.
            // For size > 2 with middle iterations, ndim stays at size + 3 until the right border.
            // So: h_axis at size, n_axis at size+1.
            let h_axis = size;
            let n_axis = size + 1;
            // Permute T to put N before h.
            let mut perm: Vec<usize> = (0..t.ndim()).collect();
            perm.swap(h_axis, n_axis); // (..., N, h, ...)
            let t_perm = t.clone().permuted_axes(perm);
            let t_perm_std = t_perm.as_standard_layout().to_owned();

            let prefix_dim: usize = t_perm_std.shape()[..h_axis].iter().product();
            let suffix_dim: usize = t_perm_std.shape()[n_axis + 1..].iter().product();
            assert_eq!(t_perm_std.shape()[h_axis], k);
            assert_eq!(t_perm_std.shape()[n_axis], k);

            // T_perm flat: (prefix, K*K, suffix). Suffix should be just the trailing 1.
            let t_3d: ndarray::Array3<f64> = t_perm_std
                .into_shape_with_order((prefix_dim, k * k, suffix_dim))
                .expect("reshape T")
                .into_dimensionality::<ndarray::Ix3>()
                .expect("3d");

            // Cell (N, S, W). Permute to (N, W, S) then flat (N*K+W, S).
            let cell_2d: Array2<f64> = cell_sliced
                .permuted_axes([0, 2, 1])  // (N, W, S)
                .as_standard_layout()
                .to_owned()
                .into_shape_with_order((k * k, k))
                .expect("reshape cell")
                .into_dimensionality::<ndarray::Ix2>()
                .expect("2d");

            // Contract: out[prefix, suffix, S] = sum_{N, W} T[prefix, N*K+W, suffix] * cell[N*K+W, S]
            let t_3d_perm = t_3d
                .permuted_axes([0, 2, 1])  // (prefix, suffix, K*K)
                .as_standard_layout()
                .to_owned();
            let t_2d_flat: Array2<f64> = t_3d_perm
                .into_shape_with_order((prefix_dim * suffix_dim, k * k))
                .expect("reshape T flat")
                .into_dimensionality::<ndarray::Ix2>()
                .expect("2d");
            let product_2d = t_2d_flat.dot(&cell_2d);  // (prefix*suffix, K)
            // Reshape to (prefix, suffix, S).
            let unshaped = product_2d
                .into_shape_with_order(IxDyn(&[prefix_dim, suffix_dim, k]))
                .expect("reshape product");
            // unshaped axes (prefix, suffix=1, S). We want (prefix, S, suffix=1).
            let unshaped_perm = unshaped.permuted_axes(IxDyn(&[0, 2, 1]));  // (prefix, S, suffix=1)
            let unshaped_perm_std = unshaped_perm.as_standard_layout().to_owned();

            // Reshape to (1, S_0, ..., S_{size-1}, 1). prefix unrolls to (1, S_0, ..., S_{size-2}); + S, + 1.
            let mut full_shape: Vec<usize> = vec![1];
            for _ in 0..(size - 1) {
                full_shape.push(k);
            }
            full_shape.push(k); // S_{size-1}
            full_shape.push(1);
            t = unshaped_perm_std
                .into_shape_with_order(IxDyn(&full_shape))
                .expect("reshape final right");
        }
    }

    t
}

/// Compute log Z by exact row-by-row contraction.
///
/// If chi == 0 (or chi >= K^size), uses exact contraction (no truncation).
/// Otherwise uses chi-truncated boundary MPS.
pub fn log_z(ctx: &PepsContext, cells: &[Array4<f64>], chi: usize) -> f64 {
    let size = ctx.size;
    let k = ctx.k_colors;
    let mut state = initial_state(k, size);

    for r in 0..size - 1 {
        let row: Vec<Array4<f64>> = (0..size).map(|x| cells[r * size + x].clone()).collect();
        state = absorb_row(state, &row);
        // Apply chi truncation after each row (except first since dim is small).
        if chi > 0 && r > 0 {
            state = truncate_state(state, chi);
        }
    }
    // Bottom row: absorb, then contract all S axes at BORDER.
    let bottom: Vec<Array4<f64>> = (0..size)
        .map(|x| cells[(size - 1) * size + x].clone())
        .collect();
    state = absorb_row(state, &bottom);

    // Slice every middle axis at BORDER to get the scalar Z.
    let mut z_arr = state;
    let n = z_arr.ndim();
    // Slice axes 1..n-1 at BORDER.
    for _ in 0..(n - 2) {
        // Slicing axis 1 each time (since slicing removes the axis).
        z_arr = z_arr.index_axis(Axis(1), BORDER as usize).to_owned();
    }
    // Now z_arr should be shape (1, 1).
    let z = z_arr.iter().sum::<f64>();
    if z <= 0.0 {
        f64::NEG_INFINITY
    } else {
        z.ln()
    }
}

/// Truncate the boundary state's K^size middle axes to a chi-bounded MPS,
/// then re-expand back to ArrayD form for the next absorb_row call.
///
/// Strategy:
///   1. Reshape state (1, K, ..., K, 1) to a matrix (1, K^size) → drop trailing 1.
///   2. SVD-sweep left-to-right to factorize into MPS of bond dim ≤ chi.
///   3. Contract the MPS back into ArrayD form for downstream absorb_row.
///   This collapses the singular-value information into the boundary state but
///   bounds memory to (size × chi × K).
///
/// Truncation is approximate — chi=infinity is exact.
fn truncate_state(state: BoundaryState, chi: usize) -> BoundaryState {
    use ndarray_linalg::SVD;
    let shape = state.shape().to_vec();
    let n = shape.len();
    if n < 4 {
        // Too small to truncate; bond dims would all be 1.
        return state;
    }
    let k = shape[1]; // assumes uniform K
    let size = n - 2; // number of K-axes
    assert_eq!(shape[0], 1);
    assert_eq!(shape[n - 1], 1);

    // Flatten state to (1, K^size).
    let total_k: usize = shape[1..n - 1].iter().product();
    let flat = state
        .into_shape_with_order(IxDyn(&[1, total_k]))
        .expect("flatten state");
    let mut leftover_mat = flat
        .into_shape_with_order((1, total_k))
        .expect("2d")
        .into_dimensionality::<ndarray::Ix2>()
        .expect("2d");

    // SVD sweep: split off one K-axis at a time.
    let mut mps_tensors: Vec<Array2<f64>> = Vec::new();
    let mut left_bond = 1usize;
    for col in 0..size {
        // leftover_mat has shape (left_bond, K^(size-col)).
        // Reshape to (left_bond * K, K^(size-col-1)).
        let rest = leftover_mat.shape()[1] / k;
        let mat = leftover_mat
            .into_shape_with_order((left_bond * k, rest))
            .expect("reshape for SVD")
            .into_dimensionality::<ndarray::Ix2>()
            .expect("2d");
        let (u_opt, s_vec, vt_opt) = mat.svd(true, true).expect("svd");
        let u = u_opt.expect("u");
        let vt = vt_opt.expect("vt");
        let keep = if chi > 0 { chi.min(s_vec.len()) } else { s_vec.len() };
        let u_kept: Array2<f64> = u.slice(ndarray::s![.., ..keep]).to_owned();
        let s_kept: Array1<f64> = s_vec.slice(ndarray::s![..keep]).to_owned();
        let vt_kept: Array2<f64> = vt.slice(ndarray::s![..keep, ..]).to_owned();
        mps_tensors.push(u_kept); // shape (left_bond*K, keep)

        // Compute S * Vt for the next step.
        let mut s_vt = vt_kept;
        for i in 0..keep {
            let scale = s_kept[i];
            let mut row = s_vt.row_mut(i);
            row.mapv_inplace(|v| v * scale);
        }
        leftover_mat = s_vt;
        left_bond = keep;
    }

    // mps_tensors now has `size` 2D matrices: U_col with shape (left_bond_col * K, right_bond_col).
    // leftover_mat at end has shape (right_bond_last, 1).
    // The product U_0 @ U_1 @ ... @ U_{size-1} @ leftover gives the original tensor (up to truncation).

    // Reconstruct the boundary state as ArrayD.
    // The MPS reads:
    //   T[i_0, i_1, ..., i_{size-1}] = U_0[i_0, b_0] U_1[b_0*K + i_1, b_1] ... U_{size-1}[b_{size-2}*K + i_{size-1}, b_{size-1}] * leftover[b_{size-1}, 0]
    // We'll contract them sequentially.
    //
    // Start with accumulator A: shape (b_0, 1) reshape U_0 to (1, K, b_0) (treating first K as physical).
    // Actually simpler: rebuild T_full = U_0 @ U_1 @ ... but each U_i is (left_bond * K, right_bond),
    // and physical K is the inner dim of left_bond*K. So:
    //
    // We'll just multiply all MPS tensors and reshape.

    // First, multiply all U_col together to reconstruct (1, K^size, last_right_bond).
    // Each U_col has shape (prev_right * K, new_right). Multiplying U_{col+1} into the
    // running accumulator: result has shape (prev_running * K, new_right). This is the
    // standard MPS-to-full conversion.

    let mut running = mps_tensors[0].clone(); // shape (1*K, b_0) = (K, b_0)
    for col in 1..size {
        let u = &mps_tensors[col]; // (b_{col-1} * K, b_col)
        // We have running: (1*K^col, b_{col-1}). Need to combine with u: (b_{col-1} * K, b_col).
        // Result: (1*K^(col+1), b_col).
        //
        // Method: running @ u_reshape where u_reshape is (b_{col-1}, K * b_col).
        let b_prev = running.shape()[1];
        let total_per_prev_row = u.shape()[1] * k;
        let u_reshape: Array2<f64> = u
            .view()
            .to_shape((b_prev, k * u.shape()[1]))
            .expect("reshape u")
            .to_owned();
        // running shape (M, b_{col-1}) @ u_reshape (b_{col-1}, K*b_col) = (M, K*b_col)
        // = (1*K^col, K*b_col). Reshape to (1*K^(col+1), b_col).
        let product = running.dot(&u_reshape);
        let m_new = product.shape()[0] * k;
        let b_col = u.shape()[1];
        running = product
            .into_shape_with_order((m_new, b_col))
            .expect("reshape running");
        let _ = total_per_prev_row;
    }
    // running shape: (K^size, last_right_bond).
    // Multiply by leftover_mat (last_right_bond, 1) → (K^size, 1).
    let final_flat = running.dot(&leftover_mat); // (K^size, 1)
    let mut full_shape: Vec<usize> = vec![1];
    for _ in 0..size {
        full_shape.push(k);
    }
    full_shape.push(1);
    final_flat
        .into_shape_with_order(IxDyn(&full_shape))
        .expect("reshape final")
}

/// High-level interface.
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
    fn log_z_2x2_matches_python() {
        let path = data_path("size_2_colors_2_c27cbb68.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(&path).unwrap();
        let ctx = PepsContext::new(Arc::new(puzzle));
        eprintln!("2x2 ctx: K={}, n_pieces={}", ctx.k_colors, ctx.n_pieces);
        let mu = vec![0.0; ctx.n_pieces];
        let pinned: Vec<Option<PieceRot>> = vec![None; ctx.size * ctx.size];
        let log_z_val = log_z_lagrangian(&ctx, &mu, &pinned, 0);
        eprintln!("log_z (2×2 exact) = {}", log_z_val);
        assert!(
            (log_z_val - 3.526361).abs() < 0.01,
            "log_z mismatch: {} vs 3.526361",
            log_z_val
        );
    }

    #[test]
    fn log_z_4x4_matches_python() {
        let path = data_path("size_4_colors_6_92cd6738.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(&path).unwrap();
        let ctx = PepsContext::new(Arc::new(puzzle));
        let mu = vec![0.0; ctx.n_pieces];
        let pinned: Vec<Option<PieceRot>> = vec![None; ctx.size * ctx.size];
        let log_z_val = log_z_lagrangian(&ctx, &mu, &pinned, 0);
        eprintln!("log_z (4×4 exact) = {}", log_z_val);
        assert!(
            (log_z_val - 5.9135).abs() < 0.01,
            "log_z mismatch: {} vs 5.9135",
            log_z_val
        );
    }

    #[test]
    fn log_z_6x6_matches_python() {
        let path = data_path("size_6_colors_6_543a4a64.csv");
        if !path.exists() { return; }
        let puzzle = load_puzzle(&path).unwrap();
        let ctx = PepsContext::new(Arc::new(puzzle));
        let mu = vec![0.0; ctx.n_pieces];
        let pinned: Vec<Option<PieceRot>> = vec![None; ctx.size * ctx.size];
        let log_z_val = log_z_lagrangian(&ctx, &mu, &pinned, 0);
        eprintln!("log_z (6×6 exact) = {}", log_z_val);
        // Python: log_Z (chi=128) = 13.754
        assert!(
            (log_z_val - 13.754).abs() < 0.05,
            "log_z mismatch: {} vs 13.754",
            log_z_val
        );
    }
}
