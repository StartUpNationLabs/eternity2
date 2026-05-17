"""W1 — Full Lagrangian dual loop using quimb boundary-MPS contraction.

This is the production-quality PEPS-Lagrangian implementation.

Algorithm:
  1. Build the PEPS for the current mu values (one numpy tensor per cell).
  2. For each cell i, compute Z_i^open via boundary-MPS contraction with
     cell i's tensor removed (its bonds dangling).
  3. From {Z_full, Z_i^open}, compute ⟨q_p⟩ = expected piece-p usage.
  4. Update mu_p ← mu_p + eta * (⟨q_p⟩ - 1).
  5. Iterate until ‖q - 1‖_∞ < tol.

After convergence, per-cell signature marginals identify the most-peaked
cells. Sequentially fix the highest-peaked cell to its top piece-rotation,
then re-run the dual on the remaining cells.

Usage:
  python3 peps_quimb_lagrangian.py <puzzle.csv> [--chi 32] [--max-iter 100]
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


def build_cell_tensor_full(
    puzzle: Puzzle,
    pos: int,
    lookup: dict,
    mu: np.ndarray,
    pinned: dict[int, tuple[int, int]] | None = None,
) -> np.ndarray:
    """Build the (K,K,K,K) cell tensor, with mu-weighted piece contributions.

    pinned: dict {pos: (pid, rot)} forces cells to a specific piece+rotation.
    For pinned cells, the cell tensor has a single non-zero entry at the
    pinned (cN, cE, cS, cW) signature.
    """
    K = puzzle.n_colors
    size = puzzle.size
    y, x = pos // size, pos % size
    n_border = y == 0
    s_border = y == size - 1
    w_border = x == 0
    e_border = x == size - 1

    T = np.zeros((K, K, K, K), dtype=np.float64)

    if pinned is not None and pos in pinned:
        pid, rot = pinned[pos]
        sig = puzzle.piece_edges(pid, rot)
        cN, cE, cS, cW = sig
        # Verify border-consistency
        if n_border and cN != BORDER: return T  # invalid pin (cell will be zero)
        if s_border and cS != BORDER: return T
        if w_border and cW != BORDER: return T
        if e_border and cE != BORDER: return T
        if not n_border and cN == BORDER: return T
        if not s_border and cS == BORDER: return T
        if not w_border and cW == BORDER: return T
        if not e_border and cE == BORDER: return T
        T[cN, cE, cS, cW] = np.exp(-mu[pid])
        return T

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
            # Skip pinned-elsewhere pieces (a piece pinned at another cell
            # cannot be at this cell)
            if pinned is not None:
                # Check if this pid is already pinned somewhere else
                already_pinned = any(p == pid for p, _ in pinned.values())
                if already_pinned:
                    continue
            T[cN, cE, cS, cW] += np.exp(-mu[pid])
    return T


def slice_cell_tensor(T: np.ndarray, pos: int, size: int) -> tuple[np.ndarray, list[str]]:
    """Slice border axes; return (sliced_tensor, axis_labels)."""
    y, x = pos // size, pos % size
    n_border = y == 0
    e_border = x == size - 1
    s_border = y == size - 1
    w_border = x == 0

    slicer = [slice(None)] * 4
    labels = []
    if n_border:
        slicer[0] = BORDER
    else:
        labels.append(f'v_{y-1}_{x}')
    if e_border:
        slicer[1] = BORDER
    else:
        labels.append(f'h_{y}_{x}')
    if s_border:
        slicer[2] = BORDER
    else:
        labels.append(f'v_{y}_{x}')
    if w_border:
        slicer[3] = BORDER
    else:
        labels.append(f'h_{y}_{x-1}')

    T_sliced = T[tuple(slicer)]
    return T_sliced, labels


def build_quimb_2d_tn(
    puzzle: Puzzle,
    mu: np.ndarray,
    pinned: dict[int, tuple[int, int]] | None = None,
    skip_cell: int | None = None,
) -> qtn.TensorNetwork:
    """Build the quimb TN.

    If skip_cell is None, returns a TensorNetwork2D (for fast boundary contraction).
    If skip_cell is given, returns a plain TensorNetwork (the topology becomes
    non-rectangular with dangling bonds).
    """
    size = puzzle.size
    lookup = build_piece_signature_lookup(puzzle)

    tensors = []
    for pos in range(size * size):
        if pos == skip_cell:
            continue
        T_full = build_cell_tensor_full(puzzle, pos, lookup, mu, pinned)
        T_sliced, labels = slice_cell_tensor(T_full, pos, size)
        y, x = pos // size, pos % size
        t = qtn.Tensor(T_sliced, inds=labels, tags=[f'CELL_{y},{x}', f'ROW{y}', f'COL{x}'])
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


def compute_log_Z(
    puzzle: Puzzle,
    mu: np.ndarray,
    chi: int,
    pinned: dict[int, tuple[int, int]] | None = None,
) -> float:
    tn2d = build_quimb_2d_tn(puzzle, mu, pinned=pinned)
    Z = tn2d.contract_boundary(max_bond=chi)
    Z_val = float(np.asarray(Z))
    if Z_val <= 0:
        return -np.inf
    return float(np.log(Z_val))


def compute_Z_open_per_cell(
    puzzle: Puzzle,
    mu: np.ndarray,
    chi: int,
    pinned: dict[int, tuple[int, int]] | None = None,
) -> dict[int, np.ndarray]:
    """For each non-pinned cell, contract the PEPS with that cell removed.
    The result has axes = the bonds that connected to the removed cell.
    """
    size = puzzle.size
    Z_open: dict[int, np.ndarray] = {}

    for skip in range(size * size):
        if pinned is not None and skip in pinned:
            continue
        tn = build_quimb_2d_tn(puzzle, mu, pinned=pinned, skip_cell=skip)
        # The output indices are the bonds that touched the removed cell.
        y, x = skip // size, skip % size
        out_inds = []
        if y > 0: out_inds.append(f'v_{y-1}_{x}')
        if x < size - 1: out_inds.append(f'h_{y}_{x}')
        if y < size - 1: out_inds.append(f'v_{y}_{x}')
        if x > 0: out_inds.append(f'h_{y}_{x-1}')

        # Use opt_einsum-style contraction for open TN
        # We can use tn.contract(output_inds=out_inds, optimize='auto').
        result = tn.contract(output_inds=out_inds, optimize='auto-hq')
        if isinstance(result, qtn.Tensor):
            arr = result.transpose(*out_inds).data
        else:
            arr = np.asarray(result)
        Z_open[skip] = arr

    return Z_open


def compute_piece_marginals(
    puzzle: Puzzle,
    mu: np.ndarray,
    chi: int,
    pinned: dict[int, tuple[int, int]] | None = None,
) -> tuple[float, np.ndarray, dict[int, np.ndarray]]:
    """Compute (log Z, ⟨q_p⟩, Z_open per cell)."""
    size = puzzle.size
    pinned = pinned or {}

    log_Z = compute_log_Z(puzzle, mu, chi, pinned)
    if not np.isfinite(log_Z):
        return -np.inf, np.zeros(puzzle.n_pieces), {}

    Z_full = float(np.exp(log_Z))
    Z_open = compute_Z_open_per_cell(puzzle, mu, chi, pinned)

    q = np.zeros(puzzle.n_pieces, dtype=np.float64)
    # Pinned cells contribute exactly 1 to the pinned piece
    for pos, (pid, _) in pinned.items():
        q[pid] += 1.0

    for i, Zi in Z_open.items():
        y, x = i // size, i % size
        n_border = y == 0
        e_border = x == size - 1
        s_border = y == size - 1
        w_border = x == 0

        # Iterate over (pid, rot) compatible with cell i's borders
        for pid in range(puzzle.n_pieces):
            # Skip if pid is pinned elsewhere
            if any(p == pid for p, _ in pinned.values()):
                continue
            for rot in range(4):
                sig = puzzle.piece_edges(pid, rot)
                cN, cE, cS, cW = sig
                if n_border and cN != BORDER: continue
                if e_border and cE != BORDER: continue
                if s_border and cS != BORDER: continue
                if w_border and cW != BORDER: continue
                if not n_border and cN == BORDER: continue
                if not e_border and cE == BORDER: continue
                if not s_border and cS == BORDER: continue
                if not w_border and cW == BORDER: continue

                # Index Zi: surviving axes are in (N, E, S, W) order for non-border sides
                idx = []
                if not n_border: idx.append(cN)
                if not e_border: idx.append(cE)
                if not s_border: idx.append(cS)
                if not w_border: idx.append(cW)
                if len(idx) == 0:
                    Z_open_val = float(Zi)
                else:
                    Z_open_val = float(Zi[tuple(idx)])
                contrib = np.exp(-mu[pid]) * Z_open_val / Z_full
                q[pid] += contrib

    return log_Z, q, Z_open


def lagrangian_loop(
    puzzle: Puzzle,
    chi: int = 32,
    eta_init: float = 0.5,
    max_iter: int = 100,
    tol: float = 1e-3,
    momentum: float = 0.0,
    eta_decay: float = 0.0,
    pinned: dict[int, tuple[int, int]] | None = None,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict[int, np.ndarray], float]:
    """Run Lagrangian dual loop. Returns (mu, q, Z_open, log_Z)."""
    mu = np.zeros(puzzle.n_pieces)
    v = np.zeros_like(mu)
    log_Z = -np.inf
    q = np.zeros(puzzle.n_pieces)
    Z_open: dict[int, np.ndarray] = {}

    t0 = time.time()
    for it in range(max_iter):
        log_Z, q, Z_open = compute_piece_marginals(puzzle, mu, chi, pinned)
        gap = q - 1.0
        gap_inf = float(np.max(np.abs(gap)))

        if verbose and (it < 10 or it % 5 == 0):
            elapsed = time.time() - t0
            print(f"  it {it:3d}: logZ={log_Z:.4f}  |q-1|∞={gap_inf:.5f}  "
                  f"max(q)={q.max():.3f}  min(q)={q.min():.3f}  t={elapsed:.1f}s",
                  flush=True)

        if gap_inf < tol:
            if verbose:
                print(f"  converged at it={it}, |q-1|∞={gap_inf:.5f}", flush=True)
            break

        v = momentum * v + gap
        eta_t = eta_init / (1.0 + eta_decay * it)
        mu = mu + eta_t * v

    return mu, q, Z_open, log_Z


def find_most_peaked_cell(
    puzzle: Puzzle,
    Z_open: dict[int, np.ndarray],
    mu: np.ndarray,
    log_Z: float,
    pinned: dict[int, tuple[int, int]],
) -> tuple[int, int, int, float] | None:
    """Find the cell + (pid, rot) with the highest P(piece=p, rot=r at cell i).

    Returns (cell_idx, pid, rot, prob) or None if no candidate.
    """
    size = puzzle.size
    Z_full = float(np.exp(log_Z))
    best = (None, None, None, -1.0)

    for i, Zi in Z_open.items():
        y, x = i // size, i % size
        n_border = y == 0
        e_border = x == size - 1
        s_border = y == size - 1
        w_border = x == 0

        for pid in range(puzzle.n_pieces):
            if any(p == pid for p, _ in pinned.values()):
                continue
            for rot in range(4):
                sig = puzzle.piece_edges(pid, rot)
                cN, cE, cS, cW = sig
                if n_border and cN != BORDER: continue
                if e_border and cE != BORDER: continue
                if s_border and cS != BORDER: continue
                if w_border and cW != BORDER: continue
                if not n_border and cN == BORDER: continue
                if not e_border and cE == BORDER: continue
                if not s_border and cS == BORDER: continue
                if not w_border and cW == BORDER: continue

                idx = []
                if not n_border: idx.append(cN)
                if not e_border: idx.append(cE)
                if not s_border: idx.append(cS)
                if not w_border: idx.append(cW)
                if len(idx) == 0:
                    Z_open_val = float(Zi)
                else:
                    Z_open_val = float(Zi[tuple(idx)])
                prob = np.exp(-mu[pid]) * Z_open_val / Z_full
                if prob > best[3]:
                    best = (i, pid, rot, prob)

    if best[0] is None:
        return None
    return best


def sequential_piece_fixing(
    puzzle: Puzzle,
    chi: int = 32,
    lagrangian_iter: int = 30,
    lagrangian_tol: float = 1e-3,
    eta: float = 0.5,
    momentum: float = 0.3,
    eta_decay: float = 0.0,
    max_pieces_to_fix: int | None = None,
    verbose: bool = True,
) -> dict[int, tuple[int, int]]:
    """
    Sequential cell-fixing: repeatedly run Lagrangian dual, find the most
    peaked cell, fix it, repeat until all cells fixed or budget exhausted.

    Returns the pinned dict {cell_idx: (pid, rot)}.
    """
    pinned: dict[int, tuple[int, int]] = {}
    n_cells = puzzle.size * puzzle.size
    max_to_fix = max_pieces_to_fix or n_cells

    while len(pinned) < max_to_fix and len(pinned) < n_cells:
        if verbose:
            print(f"\n=== piece-fixing round {len(pinned)+1}/{max_to_fix} ===", flush=True)
        mu, q, Z_open, log_Z = lagrangian_loop(
            puzzle, chi=chi, eta_init=eta, max_iter=lagrangian_iter,
            tol=lagrangian_tol, momentum=momentum, eta_decay=eta_decay,
            pinned=pinned, verbose=verbose,
        )

        best = find_most_peaked_cell(puzzle, Z_open, mu, log_Z, pinned)
        if best is None:
            if verbose:
                print("  no candidate found, stopping", flush=True)
            break
        cell, pid, rot, prob = best
        y, x = cell // puzzle.size, cell % puzzle.size
        if verbose:
            print(f"  fix cell ({y},{x}) → piece={pid} rot={rot}  prob={prob:.4f}", flush=True)
        pinned[cell] = (pid, rot)

    return pinned


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--chi", type=int, default=32)
    ap.add_argument("--eta", type=float, default=0.5)
    ap.add_argument("--max-iter", type=int, default=30)
    ap.add_argument("--tol", type=float, default=1e-3)
    ap.add_argument("--momentum", type=float, default=0.0)
    ap.add_argument("--eta-decay", type=float, default=0.0)
    ap.add_argument("--mode", default="lagrangian", choices=["lagrangian", "fix", "log_z_only"])
    ap.add_argument("--max-fixes", type=int, default=None)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} K={p.n_colors}")

    if args.mode == "log_z_only":
        t0 = time.time()
        log_Z = compute_log_Z(p, np.zeros(p.n_pieces), args.chi)
        print(f"log_Z (chi={args.chi}) = {log_Z:.6f}  ({time.time()-t0:.2f}s)")
    elif args.mode == "lagrangian":
        t0 = time.time()
        mu, q, _Zopen, log_Z = lagrangian_loop(
            p, chi=args.chi, eta_init=args.eta, max_iter=args.max_iter,
            tol=args.tol, momentum=args.momentum, eta_decay=args.eta_decay,
        )
        print(f"\nFinal: log_Z={log_Z:.4f} max(q)={q.max():.4f} min(q)={q.min():.4f}")
        print(f"Total time: {time.time()-t0:.2f}s")
    elif args.mode == "fix":
        t0 = time.time()
        pinned = sequential_piece_fixing(
            p, chi=args.chi, lagrangian_iter=args.max_iter,
            lagrangian_tol=args.tol, eta=args.eta, momentum=args.momentum,
            eta_decay=args.eta_decay, max_pieces_to_fix=args.max_fixes,
        )
        print(f"\nFinal pinned: {len(pinned)} cells fixed")
        print(f"Total time: {time.time()-t0:.2f}s")
        size = p.size
        for pos in range(size * size):
            if pos in pinned:
                pid, rot = pinned[pos]
                y, x = pos // size, pos % size
                print(f"  cell ({y},{x}): piece={pid} rot={rot}")


if __name__ == "__main__":
    main()
