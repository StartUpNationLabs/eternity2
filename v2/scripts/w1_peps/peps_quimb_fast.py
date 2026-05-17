"""W1 PEPS-Lagrangian — FAST version with cached tensor building.

Optimization over peps_quimb_lagrangian.py:
  - Build cell tensors ONCE per Lagrangian iter (cached as a list of np.ndarray).
  - For each skip_cell, rebuild only the affected tensor (just don't include it).
  - All other tensors are reused across all opened contractions.
  - This avoids the O(n_cells²) rebuild cost.

For 8×8: ~64× speedup expected.
For 16×16: ~256× speedup expected.

Validated against peps_quimb_lagrangian.py for correctness.
"""
from __future__ import annotations
import argparse
import sys
import time
import json
from pathlib import Path

import numpy as np
import quimb.tensor as qtn

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def build_piece_signature_lookup(puzzle: Puzzle):
    lookup = {}
    for pid in range(puzzle.n_pieces):
        for rot in range(4):
            sig = puzzle.piece_edges(pid, rot)
            lookup.setdefault(sig, []).append((pid, rot))
    return lookup


def build_cell_tensor_array(puzzle: Puzzle, pos: int, lookup: dict, mu: np.ndarray, pinned: dict | None = None) -> np.ndarray:
    """Build the (K, K, K, K) tensor for cell `pos` over (cN, cE, cS, cW)."""
    K = puzzle.n_colors
    size = puzzle.size
    y, x = pos // size, pos % size
    n_border = y == 0
    e_border = x == size - 1
    s_border = y == size - 1
    w_border = x == 0

    T = np.zeros((K, K, K, K), dtype=np.float64)

    if pinned and pos in pinned:
        pid, rot = pinned[pos]
        sig = puzzle.piece_edges(pid, rot)
        cN, cE, cS, cW = sig
        if (n_border and cN != BORDER) or (e_border and cE != BORDER) or \
           (s_border and cS != BORDER) or (w_border and cW != BORDER) or \
           (not n_border and cN == BORDER) or (not e_border and cE == BORDER) or \
           (not s_border and cS == BORDER) or (not w_border and cW == BORDER):
            return T
        T[cN, cE, cS, cW] = np.exp(-mu[pid])
        return T

    pinned_pids = set()
    if pinned:
        pinned_pids = {pid for pid, _ in pinned.values()}

    for sig, placements in lookup.items():
        cN, cE, cS, cW = sig
        if n_border and cN != BORDER: continue
        if e_border and cE != BORDER: continue
        if s_border and cS != BORDER: continue
        if w_border and cW != BORDER: continue
        if not n_border and cN == BORDER: continue
        if not e_border and cE == BORDER: continue
        if not s_border and cS == BORDER: continue
        if not w_border and cW == BORDER: continue
        w = 0.0
        for pid, _rot in placements:
            if pid in pinned_pids:
                continue
            w += np.exp(-mu[pid])
        if w > 0:
            T[cN, cE, cS, cW] += w
    return T


def slice_cell(T: np.ndarray, pos: int, size: int) -> tuple[np.ndarray, list[str]]:
    y, x = pos // size, pos % size
    n_border = y == 0
    e_border = x == size - 1
    s_border = y == size - 1
    w_border = x == 0

    slicer = [slice(None)] * 4
    labels = []
    if n_border: slicer[0] = BORDER
    else: labels.append(f'v_{y-1}_{x}')
    if e_border: slicer[1] = BORDER
    else: labels.append(f'h_{y}_{x}')
    if s_border: slicer[2] = BORDER
    else: labels.append(f'v_{y}_{x}')
    if w_border: slicer[3] = BORDER
    else: labels.append(f'h_{y}_{x-1}')

    return T[tuple(slicer)], labels


def build_cells_cached(puzzle: Puzzle, mu: np.ndarray, pinned: dict | None) -> list[tuple[np.ndarray, list[str]]]:
    """Build all cell tensors once. Returns list of (sliced_tensor, axis_labels)."""
    lookup = build_piece_signature_lookup(puzzle)
    cells = []
    for pos in range(puzzle.size * puzzle.size):
        T = build_cell_tensor_array(puzzle, pos, lookup, mu, pinned)
        sliced, labels = slice_cell(T, pos, puzzle.size)
        cells.append((sliced, labels))
    return cells


def build_quimb_2d_tn_from_cells(cells: list, puzzle: Puzzle, skip_cell: int = None) -> qtn.TensorNetwork:
    """Build the quimb TN from cached cells. If skip_cell is given, omit that cell."""
    size = puzzle.size
    tensors = []
    for pos in range(size * size):
        if pos == skip_cell:
            continue
        sliced, labels = cells[pos]
        y, x = pos // size, pos % size
        t = qtn.Tensor(sliced, inds=labels, tags=[f'CELL_{y},{x}', f'ROW{y}', f'COL{x}'])
        tensors.append(t)
    tn = qtn.TensorNetwork(tensors)
    if skip_cell is None:
        tn2d = qtn.TensorNetwork2D.from_TN(
            tn,
            site_tag_id='CELL_{},{}',
            x_tag_id='ROW{}',
            y_tag_id='COL{}',
            Lx=size,
            Ly=size,
        )
        return tn2d
    return tn


def compute_marginals_fast(puzzle: Puzzle, mu: np.ndarray, chi: int, pinned: dict | None) -> tuple[float, np.ndarray, dict]:
    """Compute log_Z, q, and Z_open per cell efficiently."""
    pinned = pinned or {}
    cells = build_cells_cached(puzzle, mu, pinned)
    size = puzzle.size

    # Full Z
    tn2d = build_quimb_2d_tn_from_cells(cells, puzzle)
    Z = tn2d.contract_boundary(max_bond=chi)
    Z_val = float(np.asarray(Z))
    if Z_val <= 0:
        return -np.inf, np.zeros(puzzle.n_pieces), {}
    log_Z = float(np.log(Z_val))

    # Per-cell opened
    Z_open: dict[int, np.ndarray] = {}
    for skip in range(size * size):
        if skip in pinned:
            continue
        tn = build_quimb_2d_tn_from_cells(cells, puzzle, skip_cell=skip)
        y, x = skip // size, skip % size
        out_inds = []
        if y > 0: out_inds.append(f'v_{y-1}_{x}')
        if x < size - 1: out_inds.append(f'h_{y}_{x}')
        if y < size - 1: out_inds.append(f'v_{y}_{x}')
        if x > 0: out_inds.append(f'h_{y}_{x-1}')
        result = tn.contract(output_inds=out_inds, optimize='greedy')
        if isinstance(result, qtn.Tensor):
            arr = result.transpose(*out_inds).data
        else:
            arr = np.asarray(result)
        Z_open[skip] = arr

    # Compute q
    q = np.zeros(puzzle.n_pieces, dtype=np.float64)
    for pos, (pid, _) in pinned.items():
        q[pid] += 1.0
    for i, Zi in Z_open.items():
        y, x = i // size, i % size
        n_b = y == 0
        e_b = x == size - 1
        s_b = y == size - 1
        w_b = x == 0
        pinned_pids = {pp for pp, _ in pinned.values()}
        for pid in range(puzzle.n_pieces):
            if pid in pinned_pids:
                continue
            for rot in range(4):
                sig = puzzle.piece_edges(pid, rot)
                cN, cE, cS, cW = sig
                if n_b and cN != BORDER: continue
                if e_b and cE != BORDER: continue
                if s_b and cS != BORDER: continue
                if w_b and cW != BORDER: continue
                if not n_b and cN == BORDER: continue
                if not e_b and cE == BORDER: continue
                if not s_b and cS == BORDER: continue
                if not w_b and cW == BORDER: continue
                idx = []
                if not n_b: idx.append(cN)
                if not e_b: idx.append(cE)
                if not s_b: idx.append(cS)
                if not w_b: idx.append(cW)
                if len(idx) == 0:
                    val = float(Zi)
                else:
                    val = float(Zi[tuple(idx)])
                q[pid] += np.exp(-mu[pid]) * val / Z_val

    return log_Z, q, Z_open


def lagrangian_loop_fast(
    puzzle: Puzzle,
    chi: int,
    eta_init: float,
    max_iter: int,
    tol: float,
    pinned: dict | None = None,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict, float]:
    mu = np.zeros(puzzle.n_pieces)
    log_Z = -np.inf
    q = np.zeros(puzzle.n_pieces)
    Z_open = {}
    pinned = pinned or {}

    t0 = time.time()
    for it in range(max_iter):
        log_Z, q, Z_open = compute_marginals_fast(puzzle, mu, chi, pinned)
        gap = q - 1.0
        gap_inf = float(np.max(np.abs(gap))) if len(gap) > 0 else 0.0
        if verbose and (it < 10 or it % 5 == 0):
            elapsed = time.time() - t0
            print(f"  it {it:3d}: logZ={log_Z:.4f}  |q-1|∞={gap_inf:.5f}  "
                  f"max(q)={q.max():.3f}  min(q)={q.min():.3f}  t={elapsed:.1f}s",
                  flush=True)
        if gap_inf < tol:
            print(f"  converged at it={it}", flush=True)
            break
        mu = mu + eta_init * gap
    return mu, q, Z_open, log_Z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--chi", type=int, default=64)
    ap.add_argument("--eta", type=float, default=0.3)
    ap.add_argument("--max-iter", type=int, default=100)
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--use-hints", action='store_true', help="Pin canonical hints")
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} K={p.n_colors}", flush=True)

    pinned = {}
    if args.use_hints:
        for h in p.hints:
            pinned[h.position] = (h.piece_id, h.rotation)
        print(f"Pinning {len(pinned)} hints", flush=True)

    print(f"Running fast Lagrangian (chi={args.chi}, eta={args.eta}, max_iter={args.max_iter})...", flush=True)
    t0 = time.time()
    mu, q, Z_open, log_Z = lagrangian_loop_fast(
        p, chi=args.chi, eta_init=args.eta, max_iter=args.max_iter,
        tol=args.tol, pinned=pinned,
    )
    print(f"\nFinal: log_Z={log_Z:.4f} max(q)={q.max():.4f} min(q)={q.min():.4f}", flush=True)
    print(f"Time: {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
