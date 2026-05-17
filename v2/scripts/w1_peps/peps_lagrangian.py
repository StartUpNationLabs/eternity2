"""W1 — PEPS contraction with Lagrangian piece-uniqueness for E2.

Implementation of encoding C from vault/concepts/w1-peps-design-derivation.md.

Phase 1: validate Lagrangian dual converges and per-cell marginals
peak on the correct (piece, rotation) assignment on a small puzzle
that has a known solution.

We use the EDGES-AS-VARIABLES formulation:
  - Variable per interior edge: color c ∈ [0..K] where K = n_interior_colors.
    (border edges are fixed to BORDER=0.)
  - Cell tensor at cell (i,j): function of 4 incident-edge colors:
      A[c_N, c_E, c_S, c_W] = sum over (pid, rot) such that piece pid at
                              rotation rot has edges matching (c_N, c_E, c_S, c_W),
                              weighted by Boltzmann e^{β * matched_edges} * e^{-μ_{pid}}
  - Border cell tensor: same but with c_N (or c_S, c_E, c_W) FORCED to BORDER on
    the appropriate side(s).

The Lagrangian dual is over μ_pid for each pid. At each iteration:
  1. Contract the full PEPS to get Z (partition function).
  2. For each piece p, compute ⟨q_p⟩ = ∂log(Z)/∂(-μ_p) = E[number of times p is used].
  3. Update μ_p ← μ_p + η * (⟨q_p⟩ - 1).
  4. Iterate until ‖⟨q⟩ - 1‖_∞ < tol.

This phase 1 uses exact contraction (no chi truncation) on small puzzles
to validate correctness. Phase 3 will add chi-truncated contraction for
canonical scale.

Usage:
  python3 peps_lagrangian.py <puzzle.csv> [--beta 1.0] [--eta 0.5] [--max-iter 200]
"""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

import numpy as np

# Allow running from this directory
sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def build_piece_signature_lookup(puzzle: Puzzle) -> dict[tuple[int, int, int, int], list[tuple[int, int]]]:
    """For each (N, E, S, W) color tuple, list of (piece_id, rotation) producing it."""
    lookup: dict[tuple[int, int, int, int], list[tuple[int, int]]] = {}
    for pid in range(puzzle.n_pieces):
        for rot in range(4):
            sig = puzzle.piece_edges(pid, rot)  # (top, right, bottom, left)
            lookup.setdefault(sig, []).append((pid, rot))
    return lookup


def build_cell_tensor(
    puzzle: Puzzle,
    cell_idx: int,
    lookup: dict[tuple[int, int, int, int], list[tuple[int, int]]],
    mu: np.ndarray,  # mu[pid] shadow price per piece
    beta: float,
) -> tuple[np.ndarray, list[int]]:
    """
    Build the cell tensor at the given cell index. Returns
      (tensor, axis_order)
    where tensor has shape determined by which edges are present (non-BORDER).

    For a cell, the edges are (N, E, S, W). The tensor axes are colors,
    each of dim K+1 (BORDER=0 plus 1..K interior).

    Border cells: the BORDER side has fixed color 0; the tensor on that axis is
    just a slice (effectively, the axis is dim 1 / fixed).

    Per-cell weight: e^{-mu[pid]} for each piece-rotation matching the edge signature.

    Returns the 4-d tensor; the caller will handle which axes are border-fixed.
    """
    K = puzzle.n_colors  # K+1 = total colors including BORDER
    size = puzzle.size
    y = cell_idx // size
    x = cell_idx % size

    # Identify which sides must be BORDER (only corner/edge cells)
    n_border = y == 0
    s_border = y == size - 1
    w_border = x == 0
    e_border = x == size - 1

    # Build tensor of shape (K, K, K, K) indexed by (cN, cE, cS, cW)
    T = np.zeros((K, K, K, K), dtype=np.float64)

    # Enumerate which sig values are possible:
    # If side X is border, that color must be 0; otherwise it's any 1..K-1.
    for sig, placements in lookup.items():
        cN, cE, cS, cW = sig
        # Check border consistency
        if n_border and cN != BORDER:
            continue
        if s_border and cS != BORDER:
            continue
        if w_border and cW != BORDER:
            continue
        if e_border and cE != BORDER:
            continue
        # Non-border sides must NOT be BORDER (interior edge can't be border-colored).
        if not n_border and cN == BORDER:
            continue
        if not s_border and cS == BORDER:
            continue
        if not w_border and cW == BORDER:
            continue
        if not e_border and cE == BORDER:
            continue

        # Sum Boltzmann weights over all (pid, rot) at this signature
        w = 0.0
        for pid, rot in placements:
            w += np.exp(-mu[pid])
        # The * e^{β * 4 (matched edges within this cell)} is constant across
        # configurations because internal piece-edge match is given by the
        # piece itself. The MATCHING constraint (neighbor agreement) is enforced
        # by the bonds connecting to neighbors.
        # For now we don't add a per-cell beta weight (all cells contribute
        # the same factor if filled).
        T[cN, cE, cS, cW] += w

    return T, [0, 1, 2, 3]  # axis order (N, E, S, W)


def contract_peps_exact(
    puzzle: Puzzle,
    mu: np.ndarray,
    beta: float,
) -> tuple[float, np.ndarray]:
    """
    Exact PEPS contraction for small puzzles.

    Returns:
      log_Z: log of partition function
      piece_marginals: marginals[pid] = expected count of piece pid across cells
                       = E[sum_i 1[pi(x_i) = pid]]
                       This is the gradient of -log Z w.r.t. mu[pid].

    We contract cell-by-cell. The intermediate state is the partial contraction.
    Bonds between adjacent cells share color indices.

    Strategy: contract row-by-row.
      For each row, the row tensor has 4 axes per cell:
        cN_i (north edge), cE_i (east edge), cS_i (south edge), cW_i (west edge).
      Horizontal contraction within a row: identify cE_i == cW_{i+1} (axes match).
      Vertical contraction between rows: identify cS_{i,j} == cN_{i+1,j} (axes match).

    For an MxN puzzle with each color of dim K, intermediate tensor has at most
    K^N axes after one row absorbed. For N=4, K=8: 8^4 = 4096. Manageable.
    For N=6: 8^6 ≈ 262k. Still manageable.
    For N=8: 8^8 = 16M. Larger but maybe.
    For N=16, K=23: 23^16 ≈ 4×10^21. Need MPS truncation.

    For phase 1 (N≤6), we use exact contraction.

    The piece-marginals computation uses the trick:
      ⟨q_p⟩ = -∂ log Z / ∂ mu_p
    We compute via finite differences in mu for simplicity (or use autograd-style
    derivatives via repeated contraction). For phase 1 simplicity, we use a single
    contraction that also returns per-cell tensor traces, then summing the piece
    contribution per cell.
    """
    K = puzzle.n_colors
    size = puzzle.size
    lookup = build_piece_signature_lookup(puzzle)

    # Build all cell tensors. cell_tensors[pos] -> array of shape (K,K,K,K).
    cell_tensors = []
    cell_piece_breakdown = []  # cell_piece_breakdown[pos][cN,cE,cS,cW] = list of (pid, rot, weight_factor)
    for pos in range(size * size):
        y, x = pos // size, pos % size
        n_border = y == 0
        s_border = y == size - 1
        w_border = x == 0
        e_border = x == size - 1

        T = np.zeros((K, K, K, K), dtype=np.float64)
        piece_breakdown: dict[tuple[int, int, int, int], list[tuple[int, float]]] = {}

        for sig, placements in lookup.items():
            cN, cE, cS, cW = sig
            if n_border and cN != BORDER: continue
            if s_border and cS != BORDER: continue
            if w_border and cW != BORDER: continue
            if e_border and cE != BORDER: continue
            if not n_border and cN == BORDER: continue
            if not s_border and cS == BORDER: continue
            if not w_border and cW == BORDER: continue
            if not e_border and cE == BORDER: continue

            for pid, rot in placements:
                w = np.exp(-mu[pid])
                T[cN, cE, cS, cW] += w
                piece_breakdown.setdefault((cN, cE, cS, cW), []).append((pid, w))

        cell_tensors.append(T)
        cell_piece_breakdown.append(piece_breakdown)

    # Row-by-row contraction.
    # After absorbing row r, the running tensor has axes (south of row r) for each column.
    # i.e., shape K^size (one axis per column).
    #
    # Algorithm:
    #   row_state = scalar 1
    #   for r in 0..size:
    #     compute row_tensor of shape (K^size from above_state) x (K^size for below)
    #     this is built by chain-contracting cells (r,0), (r,1), ..., (r,size-1)
    #     with horizontal bonds.
    #   merge row_state * row_tensor along the "above" axes.

    # Build row tensors:
    # For row r, the row tensor has axes:
    #   (cN_0, cN_1, ..., cN_{size-1}, cS_0, cS_1, ..., cS_{size-1})
    # = 2*size axes total, each of dim K.
    # Build by sequential horizontal contractions of cells, exploiting that
    # adjacent cells share an E-W axis.

    def build_row_tensor(r: int) -> np.ndarray:
        # Start with cell (r, 0): axes (cN_0, cE_0, cS_0, cW_0)
        # cW_0 is border, so it's the leftmost.
        T_cell = cell_tensors[r * size + 0]  # (K,K,K,K)
        # T_row has axes (cN_0, cE_0, cS_0, cW_0) currently
        # For x=0..size-1: absorb cell (r, x+1) with bond cE_x == cW_{x+1}
        row_axes = ['N0', 'E0', 'S0', 'W0']
        row = T_cell.copy()

        for x in range(1, size):
            T_next = cell_tensors[r * size + x]  # (cN_x, cE_x, cS_x, cW_x)
            # Contract row's 'E_{x-1}' axis with T_next's 'cW_x' axis.
            # Use np.einsum with explicit index strings.
            # Current row axes: 'N_0 E_? S_0 [N_1 S_1] [N_2 S_2] ... E_{x-1}'
            # Wait — let me redo this more carefully.
            #
            # Initially row = T_cell(N_0, E_0, S_0, W_0).
            # After absorbing cell(0,1) (which is (N_1, E_1, S_1, W_1)):
            #   bond: E_0 == W_1
            #   result: tensor over (N_0, S_0, W_0, N_1, E_1, S_1)
            # After absorbing cell(0,2): result over (N_0, S_0, W_0, N_1, S_1, N_2, E_2, S_2)
            # i.e., after absorbing all: (N_0..N_{size-1}, S_0..S_{size-1}, W_0, E_{size-1})
            # Border cells contribute degenerate dims (W_0 and E_{size-1} are forced to BORDER).
            # So practical shape: (K, K, ..., K) over (N_0, S_0, N_1, S_1, ..., N_{size-1}, S_{size-1})
            # plus possibly border-fixed dims that are size 1 effectively.
            #
            # Implementation: explicit einsum.
            # Current row axes string (initial): 'NESC' where N=N_0, E=E_0, S=S_0, C=W_0
            # After absorbing cell(0,1) with axes (a=N_1, b=E_1, c=S_1, d=W_1):
            #   einsum: 'NESC, abcd -> NSCNESabc' with E==d → drop E,d and reorder.
            # This is getting messy; easier to use letter-by-letter einsum.
            pass
        return row

    # Switch to a much simpler approach: explicit einsum on each cell tensor
    # with carefully named axes. Use letters.
    # For a 4x4: 16 cells. Each tensor has 4 axes. Total 64 axes; we contract 24
    # bonds (horizontal: 4*3 = 12; vertical: 3*4 = 12). 64 - 2*24 = 16 leg axes
    # if we kept them all open. But all leg axes that connect to BORDER cells
    # are forced to BORDER (color 0), so we slice them out. After slicing,
    # the contraction is just over interior bonds.

    return contract_via_einsum(puzzle, cell_tensors, mu)


def contract_via_einsum(
    puzzle: Puzzle,
    cell_tensors: list[np.ndarray],
    mu: np.ndarray,
) -> tuple[float, np.ndarray]:
    """
    Contract the full PEPS via opt_einsum.

    Each cell at (y, x) has 4 axes: N, E, S, W (each of dim K).
    Bonds:
      - Horizontal: cell(y, x).E == cell(y, x+1).W for x in 0..size-2
      - Vertical:   cell(y, x).S == cell(y+1, x).N for y in 0..size-2
      - Border:     all boundary axes are sliced to BORDER (color 0)

    Total open axes: 0 (after slicing border).
    Total bonds: 2 * size * (size - 1).

    Returns:
      log_Z (scalar)
      piece_marginals (shape: n_pieces) = expected piece-usage count.
    """
    import opt_einsum as oe

    K = puzzle.n_colors
    size = puzzle.size

    # Slice each cell tensor to remove the BORDER-fixed axes
    # Cell at (y, x): axes (N, E, S, W) each dim K.
    # If y == 0: N is forced to BORDER=0 → slice N=0.
    # If y == size-1: S is forced to BORDER=0 → slice S=0.
    # If x == 0: W is forced to BORDER=0.
    # If x == size-1: E is forced to BORDER=0.

    sliced_cells = []
    for pos in range(size * size):
        y, x = pos // size, pos % size
        T = cell_tensors[pos]
        # Build slicer
        sl: list = [slice(None)] * 4  # [N, E, S, W]
        if y == 0:
            sl[0] = BORDER
        if x == size - 1:
            sl[1] = BORDER
        if y == size - 1:
            sl[2] = BORDER
        if x == 0:
            sl[3] = BORDER
        sliced = T[tuple(sl)]
        sliced_cells.append(sliced)

    # Build einsum specification.
    # Each interior bond gets a unique label. Use:
    #   horizontal bond at (y, x→x+1): h_y_x
    #   vertical bond at (y→y+1, x): v_y_x
    # Cell labels (after slicing): only the axes that are NOT border get a label.

    # opt_einsum can handle arbitrary index labels via strings.
    # Use unique letters; if too many (> 52 = a-zA-Z), use mappings.

    bond_id = 0
    bond_labels: dict[tuple[str, int, int], int] = {}

    def get_h_bond(y, x) -> int:
        # Bond connecting (y, x).E to (y, x+1).W
        nonlocal bond_id
        key = ('h', y, x)
        if key not in bond_labels:
            bond_labels[key] = bond_id
            bond_id += 1
        return bond_labels[key]

    def get_v_bond(y, x) -> int:
        # Bond connecting (y, x).S to (y+1, x).N
        nonlocal bond_id
        key = ('v', y, x)
        if key not in bond_labels:
            bond_labels[key] = bond_id
            bond_id += 1
        return bond_labels[key]

    # For each cell, build the label list for its (non-sliced) axes.
    cell_labels = []
    for pos in range(size * size):
        y, x = pos // size, pos % size
        labels = []
        # Axes order is (N, E, S, W) but only non-border axes survive slicing.
        if y > 0:
            labels.append(get_v_bond(y - 1, x))  # N axis = vertical bond from y-1
        if x < size - 1:
            labels.append(get_h_bond(y, x))  # E axis = horizontal bond at y, x
        if y < size - 1:
            labels.append(get_v_bond(y, x))  # S axis = vertical bond at y, x
        if x > 0:
            labels.append(get_h_bond(y, x - 1))  # W axis = horizontal bond at y, x-1
        cell_labels.append(labels)

    # Now contract.
    # opt_einsum's contract_expression with int indices is supported.
    # Build operands as list of (tensor, indices) pairs.
    operands = []
    for pos in range(size * size):
        operands.append(sliced_cells[pos])
        operands.append(cell_labels[pos])
    # Output: no open indices → scalar Z
    operands.append([])

    Z = oe.contract(*operands)
    Z_scalar = float(Z)
    if Z_scalar <= 0:
        log_Z = -np.inf
    else:
        log_Z = float(np.log(Z_scalar))

    return log_Z, Z_scalar


def compute_piece_marginals_finite_diff(
    puzzle: Puzzle,
    mu: np.ndarray,
    beta: float,
    eps: float = 1e-4,
) -> tuple[float, np.ndarray]:
    """
    Compute log Z and ⟨q_p⟩ for each piece via finite differences in mu.

    ⟨q_p⟩ = -∂ log Z / ∂ mu_p

    This is O(n_pieces) contractions per evaluation. For 16-piece test, totally OK.
    """
    # Center
    cell_tensors = []
    K = puzzle.n_colors
    size = puzzle.size
    lookup = build_piece_signature_lookup(puzzle)

    def build_cells(mu_arr: np.ndarray) -> list[np.ndarray]:
        cells = []
        for pos in range(size * size):
            y, x = pos // size, pos % size
            n_border = y == 0
            s_border = y == size - 1
            w_border = x == 0
            e_border = x == size - 1

            T = np.zeros((K, K, K, K), dtype=np.float64)
            for sig, placements in lookup.items():
                cN, cE, cS, cW = sig
                if n_border and cN != BORDER: continue
                if s_border and cS != BORDER: continue
                if w_border and cW != BORDER: continue
                if e_border and cE != BORDER: continue
                if not n_border and cN == BORDER: continue
                if not s_border and cS == BORDER: continue
                if not w_border and cW == BORDER: continue
                if not e_border and cE == BORDER: continue

                for pid, rot in placements:
                    T[cN, cE, cS, cW] += np.exp(-mu_arr[pid])
            cells.append(T)
        return cells

    cells_center = build_cells(mu)
    log_Z, Z_center = contract_via_einsum(puzzle, cells_center, mu)

    q = np.zeros(puzzle.n_pieces, dtype=np.float64)
    for p in range(puzzle.n_pieces):
        mu_plus = mu.copy()
        mu_plus[p] += eps
        cells_plus = build_cells(mu_plus)
        _, Z_plus = contract_via_einsum(puzzle, cells_plus, mu_plus)
        # d log Z / d mu_p = (log Z_plus - log Z_center) / eps
        # ⟨q_p⟩ = -d log Z / d mu_p ≈ -(log Z_plus - log Z_center) / eps
        if Z_center > 0 and Z_plus > 0:
            d_log_Z = (np.log(Z_plus) - np.log(Z_center)) / eps
            q[p] = -d_log_Z
        else:
            q[p] = 0.0

    return log_Z, q


def lagrangian_dual_loop(
    puzzle: Puzzle,
    beta: float = 1.0,
    eta: float = 0.5,
    max_iter: int = 200,
    tol: float = 1e-3,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Run the Lagrangian dual loop. Returns (final mu, final q).
    """
    mu = np.zeros(puzzle.n_pieces, dtype=np.float64)

    for it in range(max_iter):
        log_Z, q = compute_piece_marginals_finite_diff(puzzle, mu, beta)
        gap = q - 1.0
        gap_inf = np.max(np.abs(gap))

        if verbose and (it < 10 or it % 10 == 0):
            print(f"  iter {it}: log_Z={log_Z:.4f} |⟨q⟩-1|_∞={gap_inf:.4f} "
                  f"max⟨q⟩={q.max():.3f} min⟨q⟩={q.min():.3f}")

        if gap_inf < tol:
            print(f"  Lagrangian dual converged at iter {it}")
            break

        # Subgradient step: μ ← μ + η (⟨q⟩ - 1)
        mu = mu + eta * gap

    return mu, q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle", help="path to puzzle CSV")
    ap.add_argument("--beta", type=float, default=1.0)
    ap.add_argument("--eta", type=float, default=0.5)
    ap.add_argument("--max-iter", type=int, default=100)
    ap.add_argument("--tol", type=float, default=1e-3)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Loaded puzzle: size={p.size} n_pieces={p.n_pieces} "
          f"interior_colors={p.n_interior_colors}")
    print(f"Total colors (incl BORDER): {p.n_colors}")
    print(f"Sigma lookup entries: ", end="")
    lookup = build_piece_signature_lookup(p)
    print(f"{len(lookup)} unique (N,E,S,W) signatures, "
          f"{sum(len(v) for v in lookup.values())} total placements")

    # Initial contraction with mu=0 (no Lagrangian)
    t0 = time.time()
    mu = np.zeros(p.n_pieces)
    log_Z, q = compute_piece_marginals_finite_diff(p, mu, args.beta)
    t_iter = time.time() - t0
    print(f"\nInitial contraction (mu=0):")
    print(f"  log Z = {log_Z:.4f}")
    print(f"  ⟨q⟩ stats: max={q.max():.3f} mean={q.mean():.3f} min={q.min():.3f}")
    print(f"  iter wall time: {t_iter:.2f}s")

    print(f"\nLagrangian dual loop (beta={args.beta}, eta={args.eta}):")
    t0 = time.time()
    mu_final, q_final = lagrangian_dual_loop(
        p, args.beta, args.eta, args.max_iter, args.tol
    )
    elapsed = time.time() - t0
    print(f"\nFinal: max⟨q⟩={q_final.max():.4f} min⟨q⟩={q_final.min():.4f}")
    print(f"Time: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
