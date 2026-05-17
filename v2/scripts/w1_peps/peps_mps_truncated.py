"""W1 — PEPS contraction via row-by-row MPS truncation (boundary MPS).

This is the Gray-Chan 2024 hyperoptimized contraction strategy:
  1. Sweep rows from top to bottom.
  2. Maintain a "boundary MPS" of bond dim ≤ χ representing the partial Z
     summed over all completed rows.
  3. For each new row, contract row-by-row into the boundary MPS, then
     truncate via SVD back to χ.

Compared to exact contraction (scaling K^size with intermediate axes), this
scales as size * size * (chi^4 * K^2) per full contraction — manageable for
canonical E2 at chi=64-128.

Phase 2 deliverable: replace exact contraction in peps_lagrangian_v2 with
this routine. Validate same log Z and ⟨q⟩ on 4x4 and 6x6 (small enough
that chi=K^size has no truncation error).

Implementation note: we represent the boundary MPS as a list of 3-axis
tensors [bond_left, physical, bond_right]. The "physical" axis runs along
the bond axes between cells in the row direction (i.e., it's the vertical
bond between rows). The left/right bonds are between adjacent boundary MPS
tensors (i.e., horizontal-direction).

This is a non-trivial implementation but well within scope for autonomous
research-grade work.
"""

from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, BORDER


def initial_boundary_mps(K: int, size: int, top_row_cells: list[np.ndarray]) -> list[np.ndarray]:
    """
    Build the initial boundary MPS as the contraction of the top row.

    The top row has cells (0, 0), (0, 1), ..., (0, size-1).
    Each cell's N axis is BORDER-sliced.

    After absorbing the top row:
      - The N axis of each cell is gone (border-sliced).
      - The W axis of cell (0, 0) is sliced (border).
      - The E axis of cell (0, size-1) is sliced (border).
      - The S axis of each cell becomes the "physical" axis of the boundary MPS.
      - The E-W bonds within the row become "left-right" bonds of the boundary MPS.

    For a row of size cells:
      Cell (0, 0) sliced shape: (E_0, S_0) — assuming no N or W axis.
      Cell (0, 1) sliced shape: (E_1, S_1, W_1) — W_1 connects to E_0.
      Cell (0, x) for 1 ≤ x ≤ size-2: (E_x, S_x, W_x).
      Cell (0, size-1): (S_{size-1}, W_{size-1}).

    We absorb left-to-right, producing an MPS tensor per cell.
    MPS tensor at column x has shape (bond_left, physical=S_x, bond_right).
      - bond_left = W_x axis (or 1 if x=0, dangling)
      - bond_right = E_x axis (or 1 if x=size-1, dangling)

    Order of axes in input cells_sliced (after slicing):
      For cell (0, 0) with n_border=True, w_border=True: axes = (E, S)
      For cell (0, x), 0 < x < size-1: axes = (E, S, W)
      For cell (0, size-1): axes = (S, W)
    """
    mps = []
    for x in range(size):
        T = top_row_cells[x]
        # Reorder axes to (left, physical, right) = (W, S, E)
        if x == 0 and size == 1:
            # Only one cell, no horizontal bonds: T has just (S,) axis.
            # mps tensor: (1, K, 1)
            assert T.ndim == 1
            mps.append(T[None, :, None])
        elif x == 0:
            # Cell (0, 0): n_border, w_border. Axes are (E, S).
            # MPS shape: (1, S, E) → (1, K, K)
            assert T.ndim == 2, f"top-left cell tensor must have 2 axes, got {T.ndim}"
            # T[E, S]; we want (left=1, phys=S, right=E)
            mps.append(T.transpose(1, 0)[None, :, :])  # shape (1, K, K)
        elif x == size - 1:
            # Cell (0, size-1): n_border, e_border. Axes are (S, W).
            # MPS shape: (W, S, 1)
            assert T.ndim == 2
            # T[S, W] → (W, S, 1)
            mps.append(T.transpose(1, 0)[:, :, None])
        else:
            # Cell (0, x), 0 < x < size-1: axes are (E, S, W).
            # MPS shape: (W, S, E)
            assert T.ndim == 3
            # T[E, S, W] → (W, S, E)
            mps.append(T.transpose(2, 1, 0))
    return mps


def absorb_row(
    mps: list[np.ndarray],
    row_cells: list[np.ndarray],
    size: int,
    is_bottom_row: bool,
    chi: int,
) -> list[np.ndarray]:
    """
    Absorb the next row into the boundary MPS, then truncate to bond dim chi.

    For non-bottom row:
      - Each row cell has 4 axes: (N, E, S, W). N is the bond from the previous
        row (= physical of incoming MPS at column x). S becomes the new physical.
        E-W become MPS bonds.
      - After absorption: new MPS where each tensor at column x has shape
        (left * cell_W, physical=S, right * cell_E).
      - Then SVD-truncate left and right bonds back to chi.

    For bottom row:
      - Each row cell has 3 axes (N, E, W) — S is sliced.
      - After absorption: contract along N axis with incoming MPS, then
        contract entire row to a scalar (since no remaining physical axis).
    """
    new_mps = []
    for x in range(size):
        T_cell = row_cells[x]
        M = mps[x]  # shape (left, phys=N, right)

        # Reorder cell axes to (N, W, S, E):
        # The cell has axes that may be sliced.
        # We need to identify the order: build_cell_tensor produces (cN, cE, cS, cW).
        # slice_border slices in the order N, E, S, W:
        #   if y_border_top (= we're at top row): N sliced, surviving = (E, S, W)
        #   if y_border_bot (= we're at bottom row): S sliced, surviving = (N, E, W)
        #   ... etc.
        # For row r > 0, y_border_top is False, so N is NOT sliced.
        # For row r < size-1, y_border_bot is False, so S is NOT sliced.

        # Let's enumerate the cases:
        # x=0 (w_border): W sliced.
        # x=size-1 (e_border): E sliced.
        # is_bottom_row (s_border): S sliced.
        # We're NOT in top row here, so N is never sliced.

        # Surviving axes (in original (N, E, S, W) order):
        n_border = False  # we're absorbing rows r >= 1
        s_border = is_bottom_row
        w_border = (x == 0)
        e_border = (x == size - 1)
        surv = []
        if not n_border: surv.append('N')
        if not e_border: surv.append('E')
        if not s_border: surv.append('S')
        if not w_border: surv.append('W')

        # We expect T_cell.shape to have len(surv) axes.
        assert T_cell.ndim == len(surv), f"cell ({x}) expected {len(surv)} axes, got {T_cell.ndim} (surv={surv})"

        # Reshape to canonical order (N, W, S, E) or whichever subset survives.
        # We'll permute T_cell so its axes are in order [N, W, S, E] (subset).
        target_order = []
        for label in ['N', 'W', 'S', 'E']:
            if label in surv:
                target_order.append(surv.index(label))
        T_cell = T_cell.transpose(*target_order)
        # Now T_cell axes are (N, W, S, E) restricted to surviving.

        # The MPS tensor M has axes (left, phys=N, right).
        # We need to contract M's phys axis with T_cell's N axis.
        # Result has axes (left, [W if not w_border], [S if not s_border], [E if not e_border], right).
        # We'll then merge (left, W) into a new left bond, and (right, E) into a new right bond.
        # The physical axis for the new MPS is S (if not s_border) or absent if s_border.

        # Use einsum
        M_left, M_phys, M_right = M.shape  # M_phys must equal T_cell.shape[0] (N axis size)
        assert M_phys == T_cell.shape[0], (
            f"col {x}: MPS phys dim {M_phys} ≠ cell N dim {T_cell.shape[0]}. "
            f"MPS shape {M.shape}, cell shape {T_cell.shape}, surv={surv}"
        )

        # T_cell shape after transpose: (N, W, S, E) restricted
        # Indices for T_cell: 'n' + ('w' if not w_border else '') + ('s' if not s_border else '') + ('e' if not e_border else '')
        n_idx = 'n'
        w_idx = 'w' if not w_border else ''
        s_idx = 's' if not s_border else ''
        e_idx = 'e' if not e_border else ''
        cell_idx = n_idx + w_idx + s_idx + e_idx

        # MPS indices
        mps_idx = 'lnr'

        # Output indices: l, w (if not w_border), s (if not s_border), e (if not e_border), r
        out_idx = 'l' + w_idx + s_idx + e_idx + 'r'

        # Einsum string
        einsum_str = f'{mps_idx},{cell_idx}->{out_idx}'
        combined = np.einsum(einsum_str, M, T_cell)
        # combined shape: (l, [w], [s], [e], r)

        # Now: merge (l, w) into new left bond, (r, e) into new right bond.
        # For boundary cells (w_border or e_border), one of these collapses.
        # New shape: (new_left, phys=s (if not s_border, else 1), new_right)

        if w_border and e_border:
            new_left_dim = M_left  # no w
            new_right_dim = M_right  # no e
            if s_border:
                # combined shape: (l, r)
                # No physical axis. We'd need this for the bottom row.
                # combined shape is (M_left, M_right). Squeeze to (new_left, 1, new_right)?
                phys_dim = 1
                new_T = combined.reshape(new_left_dim, phys_dim, new_right_dim)
            else:
                # combined shape: (l, s, r)
                new_T = combined  # already (left, phys, right)
        elif w_border:
            new_left_dim = M_left
            # combined shape: (l, [s], e, r)
            if s_border:
                # shape (l, e, r)
                phys_dim = 1
                # merge e with r
                new_right_dim = combined.shape[1] * combined.shape[2]
                new_T = combined.reshape(new_left_dim, phys_dim, new_right_dim)
            else:
                # shape (l, s, e, r)
                phys_dim = combined.shape[1]
                # merge e with r
                new_right_dim = combined.shape[2] * combined.shape[3]
                new_T = combined.reshape(new_left_dim, phys_dim, new_right_dim)
        elif e_border:
            new_right_dim = M_right
            # combined shape: (l, w, [s], r)
            if s_border:
                # shape (l, w, r)
                phys_dim = 1
                new_left_dim = combined.shape[0] * combined.shape[1]
                new_T = combined.reshape(new_left_dim, phys_dim, new_right_dim)
            else:
                # shape (l, w, s, r)
                phys_dim = combined.shape[2]
                new_left_dim = combined.shape[0] * combined.shape[1]
                new_T = combined.reshape(new_left_dim, phys_dim, new_right_dim)
        else:
            # combined shape: (l, w, [s], e, r)
            if s_border:
                # (l, w, e, r)
                phys_dim = 1
                new_left_dim = combined.shape[0] * combined.shape[1]
                new_right_dim = combined.shape[2] * combined.shape[3]
                # Need to reshape: combined is (l, w, e, r). We want (l*w, 1, e*r).
                new_T = combined.transpose(0, 1, 2, 3).reshape(new_left_dim, phys_dim, new_right_dim)
            else:
                # (l, w, s, e, r)
                phys_dim = combined.shape[2]
                new_left_dim = combined.shape[0] * combined.shape[1]
                new_right_dim = combined.shape[3] * combined.shape[4]
                new_T = combined.transpose(0, 1, 2, 3, 4).reshape(new_left_dim, phys_dim, new_right_dim)

        new_mps.append(new_T)

    # Now SVD-compress the new MPS.
    # Left-to-right sweep: at each pair (M_x, M_{x+1}), compute SVD of M_x's right bond,
    # truncate to chi, absorb singular values into M_{x+1}.

    new_mps = compress_mps(new_mps, chi)
    return new_mps


def compress_mps(mps: list[np.ndarray], chi: int) -> list[np.ndarray]:
    """Compress an MPS to maximum bond dimension chi via left-to-right SVD sweep."""
    n = len(mps)
    if n <= 1:
        return mps
    # Left-to-right sweep with SVD
    for i in range(n - 1):
        M = mps[i]
        l, p, r = M.shape
        # Reshape to (l*p, r)
        M_mat = M.reshape(l * p, r)
        U, S, Vt = np.linalg.svd(M_mat, full_matrices=False)
        # Truncate to chi
        keep = min(chi, len(S))
        U = U[:, :keep]
        S = S[:keep]
        Vt = Vt[:keep, :]
        # mps[i] = U.reshape(l, p, keep)
        mps[i] = U.reshape(l, p, keep)
        # Absorb S * Vt into mps[i+1]
        SVt = (S[:, None] * Vt)
        mps[i + 1] = np.einsum('lr,rps->lps', SVt, mps[i + 1])
    # Right-to-left sweep to canonical form (optional but stabilizes)
    for i in range(n - 1, 0, -1):
        M = mps[i]
        l, p, r = M.shape
        M_mat = M.reshape(l, p * r)
        U, S, Vt = np.linalg.svd(M_mat, full_matrices=False)
        keep = min(chi, len(S))
        U = U[:, :keep]
        S = S[:keep]
        Vt = Vt[:keep, :]
        mps[i] = Vt.reshape(keep, p, r)
        US = U * S[None, :]
        mps[i - 1] = np.einsum('lps,sr->lpr', mps[i - 1], US)
    return mps


def contract_full_mps(mps: list[np.ndarray]) -> float:
    """Contract the final MPS to a scalar Z (after all rows absorbed; physical=1)."""
    # After bottom row absorbed, each MPS tensor has phys_dim=1.
    # Multiply out left-to-right.
    n = len(mps)
    result = mps[0]  # shape (1, 1, r)
    for i in range(1, n):
        # result has shape (1, 1, r), mps[i] has shape (r, 1, r')
        # contract over r
        result = np.einsum('lpr,rqs->lpqs', result, mps[i])
        # Squeeze p and q since they are 1
        # result shape: (1, 1, 1, r')
        # Reshape to (1, 1, r')
        result = result.reshape(result.shape[0], result.shape[1] * result.shape[2], result.shape[3])
    # Final shape: (1, 1, 1). Scalar.
    return float(result.squeeze())


def compute_log_Z_chi(
    puzzle: Puzzle,
    cell_tensors_sliced: list[np.ndarray],
    chi: int,
) -> float:
    """Compute log Z via row-by-row boundary MPS with bond dim chi."""
    size = puzzle.size
    K = puzzle.n_colors

    # Initialize MPS from top row
    top_row = [cell_tensors_sliced[0 * size + x] for x in range(size)]
    mps = initial_boundary_mps(K, size, top_row)

    # Absorb rows 1 through size-1
    for r in range(1, size):
        row = [cell_tensors_sliced[r * size + x] for x in range(size)]
        mps = absorb_row(mps, row, size, is_bottom_row=(r == size - 1), chi=chi)

    Z = contract_full_mps(mps)
    if Z <= 0:
        return -np.inf
    return float(np.log(Z))


if __name__ == "__main__":
    # Quick smoke test using the 4×4 puzzle
    import time
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from peps_lagrangian_v2 import build_piece_signature_lookup, build_cell_tensor, slice_border
    from puzzle_loader import load_puzzle

    p = load_puzzle("../data/generated/size_4_colors_6_92cd6738.csv")
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} K={p.n_colors}")

    lookup = build_piece_signature_lookup(p)
    mu = np.zeros(p.n_pieces)
    cells_full = [build_cell_tensor(p, pos, lookup, mu) for pos in range(p.size * p.size)]
    cells_sliced = [slice_border(cells_full[pos], pos, p.size) for pos in range(p.size * p.size)]

    for chi in [4, 8, 16, 64]:
        t0 = time.time()
        log_Z = compute_log_Z_chi(p, cells_sliced, chi)
        dt = time.time() - t0
        print(f"  chi={chi}: log_Z={log_Z:.6f}  ({dt:.3f}s)")

    # Compare against exact (from v2 module)
    from peps_lagrangian_v2 import compute_piece_marginals_analytic
    t0 = time.time()
    log_Z_exact, _ = compute_piece_marginals_analytic(p, mu)
    dt = time.time() - t0
    print(f"  exact (v2 analytic): log_Z={log_Z_exact:.6f}  ({dt:.3f}s)")
