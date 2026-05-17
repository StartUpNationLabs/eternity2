"""W1 — PEPS with Lagrangian piece-uniqueness via quimb.

Quimb (Quantum Information Many-Body Python) provides battle-tested
2D tensor-network primitives:
  - quimb.tensor.TensorNetwork2D
  - quimb.tensor.TN_from_edges_and_fill_fn
  - quimb.tensor.tensor_2d_compress (boundary-MPS truncation)

Encoding (edges-as-variables):
  - Vertices = cells (16×16 grid for canonical E2).
  - Edges = horizontal and vertical adjacencies between cells.
  - Each edge has a "color" variable of dim K = n_interior_colors + 1.
  - At each cell vertex, place a tensor over 4 edge variables (N, E, S, W),
    each of dim K.
  - Cell tensor value: number of (piece, rotation) compatible with given
    (cN, cE, cS, cW) signature, weighted by e^{-mu[pid]} per piece.
  - Border edges: fixed to BORDER color (= 0); implemented by making the
    border-adjacent axis of dim 1 (fixed slice) OR by hooking up to a
    fixed-value "boundary" tensor.

For the Lagrangian dual:
  - At each iteration, rebuild cell tensors with current mu.
  - Use quimb's contract_boundary_mps to get log Z.
  - Use quimb's per-tensor opening to extract per-cell piece marginals.

This is dramatically simpler than rolling our own MPS truncation.

Usage:
  python3 peps_quimb.py <puzzle.csv> [--chi 32] [--max-iter 100] [--eta 0.5]
"""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import quimb.tensor as qtn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def build_piece_signature_lookup(puzzle: Puzzle) -> dict[tuple[int, int, int, int], list[tuple[int, int]]]:
    lookup: dict[tuple[int, int, int, int], list[tuple[int, int]]] = {}
    for pid in range(puzzle.n_pieces):
        for rot in range(4):
            sig = puzzle.piece_edges(pid, rot)
            lookup.setdefault(sig, []).append((pid, rot))
    return lookup


def build_cell_tensor_array(puzzle: Puzzle, pos: int, lookup: dict, mu: np.ndarray) -> np.ndarray:
    """Build the per-cell tensor as a 4-axis numpy array (cN, cE, cS, cW),
    each axis of dim K."""
    K = puzzle.n_colors
    size = puzzle.size
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

        for pid, _rot in placements:
            T[cN, cE, cS, cW] += np.exp(-mu[pid])
    return T


def build_quimb_peps(puzzle: Puzzle, mu: np.ndarray) -> qtn.TensorNetwork:
    """Build a quimb TensorNetwork representing the E2 PEPS for given mu.

    Each cell (y, x) is a tensor with up to 4 bonds:
      - N bond: shared with cell (y-1, x) if y > 0
      - E bond: shared with cell (y, x+1) if x < size-1
      - S bond: shared with cell (y+1, x) if y < size-1
      - W bond: shared with cell (y, x-1) if x > 0

    Border edges (no shared neighbor) are handled by slicing the cell tensor
    to fix the border-axis to BORDER (= 0). After slicing, the cell tensor
    has only the non-border axes.

    Bond names use the convention: 'h_y_x' for horizontal (between (y,x) and (y,x+1))
    and 'v_y_x' for vertical (between (y,x) and (y+1,x)).
    Cell tags: 'CELL_y_x'.
    """
    size = puzzle.size
    K = puzzle.n_colors
    lookup = build_piece_signature_lookup(puzzle)

    tensors = []
    for pos in range(size * size):
        y, x = pos // size, pos % size
        T_full = build_cell_tensor_array(puzzle, pos, lookup, mu)  # (cN, cE, cS, cW)

        # Determine surviving axes (non-border) and their bond names.
        n_border = y == 0
        e_border = x == size - 1
        s_border = y == size - 1
        w_border = x == 0

        inds = []
        slicer = [slice(None)] * 4
        if n_border:
            slicer[0] = BORDER
        else:
            inds.append(f'v_{y-1}_{x}')  # N axis = vertical bond from cell above
        if e_border:
            slicer[1] = BORDER
        else:
            inds.append(f'h_{y}_{x}')  # E axis = horizontal bond
        if s_border:
            slicer[2] = BORDER
        else:
            inds.append(f'v_{y}_{x}')  # S axis = vertical bond
        if w_border:
            slicer[3] = BORDER
        else:
            inds.append(f'h_{y}_{x-1}')  # W axis = horizontal bond from left

        T_sliced = T_full[tuple(slicer)]
        # T_sliced shape and inds order: depends on which axes survived.
        # The order in our inds list matches the order axes survive in slicing.
        # numpy slicing preserves the order of surviving axes, so this aligns.

        tag = f'CELL_{y},{x}'
        t = qtn.Tensor(T_sliced, inds=inds, tags=[tag, f'ROW{y}', f'COL{x}'])
        tensors.append(t)

    tn = qtn.TensorNetwork(tensors)
    return tn


def compute_log_Z_quimb(puzzle: Puzzle, mu: np.ndarray, chi: int = 32) -> float:
    """Compute log Z using quimb's boundary-MPS contraction."""
    tn = build_quimb_peps(puzzle, mu)
    # Tag tensors as 2D and contract via boundary MPS
    # Convert to 2D tensor network with row/col tags
    tn2d = qtn.TensorNetwork2D.from_TN(
        tn,
        site_tag_id='CELL_{},{}',
        x_tag_id='ROW{}',
        y_tag_id='COL{}',
        Lx=puzzle.size,
        Ly=puzzle.size,
    )
    # Actually let's just contract using quimb's generic facilities.
    # The boundary contraction wants a 2D structure. Let me try the simpler
    # approach: use tn.contract directly with optimize='auto' or 'auto-hq'.
    Z = tn.contract(optimize='auto-hq', output_inds=[])
    Z_val = float(np.asarray(Z))
    if Z_val <= 0:
        return -np.inf
    return float(np.log(Z_val))


def compute_log_Z_via_boundary_mps(puzzle: Puzzle, mu: np.ndarray, chi: int = 32) -> float:
    """Compute log Z using quimb's TensorNetwork2D.contract_boundary_mps."""
    tn = build_quimb_peps(puzzle, mu)

    # Need to convert to TensorNetwork2D. Quimb expects each cell tagged with
    # both a site tag (unique) and a row tag and col tag.
    # Then it can do row-by-row MPS contraction.

    size = puzzle.size
    tn2d = qtn.TensorNetwork2D.from_TN(
        tn,
        site_tag_id='CELL_{},{}',
        x_tag_id='ROW{}',
        y_tag_id='COL{}',
        Lx=size,
        Ly=size,
    )

    # Quimb's contract_boundary takes max_bond=chi.
    Z = tn2d.contract_boundary(max_bond=chi)
    Z_val = float(np.asarray(Z))
    if Z_val <= 0:
        return -np.inf
    return float(np.log(Z_val))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--chi", type=int, default=32)
    ap.add_argument("--mode", default="auto", choices=["auto", "boundary_mps"])
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} K={p.n_colors}")

    mu = np.zeros(p.n_pieces)

    if args.mode == "auto":
        t0 = time.time()
        log_Z = compute_log_Z_quimb(p, mu, args.chi)
        print(f"auto contract: log_Z = {log_Z:.6f}  ({time.time()-t0:.2f}s)")
    else:
        for chi in [4, 8, 16, 32, 64, 128]:
            t0 = time.time()
            log_Z = compute_log_Z_via_boundary_mps(p, mu, chi)
            print(f"boundary_mps chi={chi:3d}: log_Z = {log_Z:.6f}  ({time.time()-t0:.2f}s)")


if __name__ == "__main__":
    main()
