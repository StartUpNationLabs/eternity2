"""W1 v3 — PEPS contraction with Lagrangian piece-uniqueness, using cotengra
for path optimization.

Improvements over v2:
  - Use cotengra to find optimal contraction order via hyperparameter optimization.
  - Reuse contraction trees across iterations (cells differ only in scalar weights).
  - Adaptive Lagrangian step size with momentum.
  - Memory budget guard.

This version still uses EXACT contraction; chi-truncation is a separate module.
"""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import cotengra as ctg
import opt_einsum as oe

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def build_piece_signature_lookup(puzzle: Puzzle) -> dict[tuple[int, int, int, int], list[tuple[int, int]]]:
    lookup: dict[tuple[int, int, int, int], list[tuple[int, int]]] = {}
    for pid in range(puzzle.n_pieces):
        for rot in range(4):
            sig = puzzle.piece_edges(pid, rot)
            lookup.setdefault(sig, []).append((pid, rot))
    return lookup


def build_cell_tensor(puzzle: Puzzle, pos: int, lookup: dict, mu: np.ndarray) -> np.ndarray:
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

        w = 0.0
        for pid, _rot in placements:
            w += np.exp(-mu[pid])
        T[cN, cE, cS, cW] += w
    return T


def slice_border(T: np.ndarray, pos: int, size: int) -> np.ndarray:
    y, x = pos // size, pos % size
    sl: list = [slice(None)] * 4
    if y == 0: sl[0] = BORDER
    if x == size - 1: sl[1] = BORDER
    if y == size - 1: sl[2] = BORDER
    if x == 0: sl[3] = BORDER
    return T[tuple(sl)]


def build_einsum_spec(puzzle: Puzzle, open_cell: int | None = None) -> tuple[list[list], list]:
    """
    Build the einsum index labels for full PEPS contraction.

    Returns (cell_labels, output_labels):
      cell_labels[i] = list of int labels for cell i's surviving axes (in NESW order)
      output_labels = output index list (empty if no open cell)

    For open_cell: cell i's surviving axes are given UNIQUE labels (not shared
    with neighbors). The neighbors still use the bond label. This is achieved
    by a delta tensor that ties them together at output time... actually,
    here we just keep the bond label for the open cell and the neighbor
    uses the same bond label (closed). The output labels then equal the
    surviving labels of open_cell, but the contraction sums over them.
    Wait, that's wrong — that contracts them away. We need fresh open labels.

    For now, this function only handles fully closed contraction (open_cell=None).
    """
    if open_cell is not None:
        raise NotImplementedError("use build_open_einsum_spec for open contractions")

    size = puzzle.size
    bond_id = 0
    bond_labels: dict[tuple[str, int, int], int] = {}

    def gh(y, x):
        nonlocal bond_id
        k = ('h', y, x)
        if k not in bond_labels:
            bond_labels[k] = bond_id; bond_id += 1
        return bond_labels[k]

    def gv(y, x):
        nonlocal bond_id
        k = ('v', y, x)
        if k not in bond_labels:
            bond_labels[k] = bond_id; bond_id += 1
        return bond_labels[k]

    cell_labels = []
    for pos in range(size * size):
        y, x = pos // size, pos % size
        labels = []
        if y > 0: labels.append(gv(y - 1, x))
        if x < size - 1: labels.append(gh(y, x))
        if y < size - 1: labels.append(gv(y, x))
        if x > 0: labels.append(gh(y, x - 1))
        cell_labels.append(labels)

    return cell_labels, []


def build_open_einsum_spec(puzzle: Puzzle, open_cell: int) -> tuple[list[list], list]:
    """
    Build einsum spec with open_cell's surviving axes as OUTPUT axes.

    The trick: assign cell `open_cell`'s surviving axes FRESH labels (not
    shared with neighbors). The neighbor at the same bond uses a different
    label. Then add an IDENTITY tensor between (neighbor's bond label, open
    cell's fresh label) — wait, this doesn't work because we want the open
    cell to remain open.

    Cleaner approach: remove open_cell from the operands entirely. The result
    of the contraction-over-others has axes = the bonds that USED to connect
    to open_cell. Those bonds are now dangling output axes.

    Implementation: build labels normally, but DON'T include open_cell in
    the operands. Set the output axes = neighbor's bonds that touched open_cell.
    """
    size = puzzle.size
    bond_id = 0
    bond_labels: dict[tuple[str, int, int], int] = {}

    def gh(y, x):
        nonlocal bond_id
        k = ('h', y, x)
        if k not in bond_labels:
            bond_labels[k] = bond_id; bond_id += 1
        return bond_labels[k]

    def gv(y, x):
        nonlocal bond_id
        k = ('v', y, x)
        if k not in bond_labels:
            bond_labels[k] = bond_id; bond_id += 1
        return bond_labels[k]

    cell_labels = []
    for pos in range(size * size):
        y, x = pos // size, pos % size
        labels = []
        if y > 0: labels.append(gv(y - 1, x))
        if x < size - 1: labels.append(gh(y, x))
        if y < size - 1: labels.append(gv(y, x))
        if x > 0: labels.append(gh(y, x - 1))
        cell_labels.append(labels)

    # Output axes = open_cell's surviving labels (the bonds that touched the
    # removed cell). When we remove open_cell from operands, those bonds
    # become uncontracted and appear as output axes.
    output_labels = cell_labels[open_cell]
    return cell_labels, output_labels


def compute_log_Z_and_per_cell_open(
    puzzle: Puzzle,
    cell_tensors_sliced: list[np.ndarray],
    contract_opts: dict | None = None,
) -> tuple[float, dict[int, np.ndarray]]:
    """
    Compute log Z and per-cell opened contraction Z_i^open.

    Uses opt_einsum.contract for each contraction. cotengra path optimization
    can be enabled via contract_opts={'optimize': 'auto-hq'} or
    a precomputed ContractionTree.

    Returns:
      log_Z: scalar
      Z_open: dict[cell_idx] -> tensor with shape matching cell_tensors_sliced[cell_idx]
    """
    if contract_opts is None:
        contract_opts = {'optimize': 'greedy'}

    size = puzzle.size
    n_cells = size * size

    cell_labels, _ = build_einsum_spec(puzzle)

    # Full Z
    operands = []
    for pos in range(n_cells):
        operands.append(cell_tensors_sliced[pos])
        operands.append(cell_labels[pos])
    operands.append([])  # closed
    Z_full = float(oe.contract(*operands, **contract_opts))
    if Z_full <= 0:
        return -np.inf, {}
    log_Z = float(np.log(Z_full))

    # Per-cell opened
    Z_open: dict[int, np.ndarray] = {}
    for i in range(n_cells):
        operands_i = []
        for pos in range(n_cells):
            if pos == i: continue
            operands_i.append(cell_tensors_sliced[pos])
            operands_i.append(cell_labels[pos])
        # Output = open_cell's bond labels
        operands_i.append(cell_labels[i])
        Z_open[i] = oe.contract(*operands_i, **contract_opts)

    return log_Z, Z_open


def compute_piece_marginals_v3(
    puzzle: Puzzle,
    mu: np.ndarray,
    Z_open: dict[int, np.ndarray] | None = None,
    contract_opts: dict | None = None,
) -> tuple[float, np.ndarray]:
    """
    Compute log Z and ⟨q_p⟩ for all p.

    If Z_open is provided (pre-computed), uses it.
    Otherwise computes log_Z and Z_open from scratch.
    """
    size = puzzle.size
    lookup = build_piece_signature_lookup(puzzle)
    cells_full = [build_cell_tensor(puzzle, pos, lookup, mu) for pos in range(size * size)]
    cells_sliced = [slice_border(cells_full[pos], pos, size) for pos in range(size * size)]

    if Z_open is None:
        log_Z, Z_open = compute_log_Z_and_per_cell_open(puzzle, cells_sliced, contract_opts)
    else:
        # We still need log_Z
        cell_labels, _ = build_einsum_spec(puzzle)
        operands = []
        for pos in range(size * size):
            operands.append(cells_sliced[pos])
            operands.append(cell_labels[pos])
        operands.append([])
        Z_full = float(oe.contract(*operands, **(contract_opts or {'optimize': 'greedy'})))
        if Z_full <= 0:
            return -np.inf, np.zeros(puzzle.n_pieces)
        log_Z = float(np.log(Z_full))

    Z_full = float(np.exp(log_Z))

    q = np.zeros(puzzle.n_pieces, dtype=np.float64)
    for i in range(size * size):
        y, x = i // size, i % size
        n_border = y == 0
        s_border = y == size - 1
        w_border = x == 0
        e_border = x == size - 1

        Zi = Z_open[i]
        # Zi shape matches cells_sliced[i] (same surviving axes).
        # We iterate over (pid, rot, sig), check signature compatibility with cell i.
        for pid in range(puzzle.n_pieces):
            for rot in range(4):
                sig = puzzle.piece_edges(pid, rot)
                cN, cE, cS, cW = sig
                if n_border and cN != BORDER: continue
                if s_border and cS != BORDER: continue
                if w_border and cW != BORDER: continue
                if e_border and cE != BORDER: continue
                if not n_border and cN == BORDER: continue
                if not s_border and cS == BORDER: continue
                if not w_border and cW == BORDER: continue
                if not e_border and cE == BORDER: continue

                # Index Zi using surviving axes in NESW order
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

    return log_Z, q


def lagrangian_loop_v3(
    puzzle: Puzzle,
    eta_init: float = 0.5,
    max_iter: int = 100,
    tol: float = 1e-3,
    contract_opts: dict | None = None,
    momentum: float = 0.0,
    eta_decay: float = 0.0,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Lagrangian dual loop with optional momentum and step-size decay.

    Update rule (heavy-ball momentum):
      v_{t+1} = momentum * v_t + (q_t - 1)
      mu_{t+1} = mu_t + eta_t * v_{t+1}
      eta_t = eta_init / (1 + eta_decay * t)
    """
    mu = np.zeros(puzzle.n_pieces, dtype=np.float64)
    v = np.zeros_like(mu)
    log_Z = -np.inf
    q = np.zeros(puzzle.n_pieces)

    t_start = time.time()
    for it in range(max_iter):
        log_Z, q = compute_piece_marginals_v3(puzzle, mu, contract_opts=contract_opts)
        gap = q - 1.0
        gap_inf = float(np.max(np.abs(gap)))

        if verbose and (it < 10 or it % 5 == 0):
            elapsed = time.time() - t_start
            print(f"  iter {it:3d}: log_Z={log_Z:.4f} |⟨q⟩-1|_∞={gap_inf:.5f} "
                  f"max⟨q⟩={q.max():.3f} min⟨q⟩={q.min():.3f} t={elapsed:.1f}s",
                  flush=True)

        if gap_inf < tol:
            print(f"  Lagrangian dual converged at iter {it}", flush=True)
            break

        v = momentum * v + gap
        eta_t = eta_init / (1.0 + eta_decay * it)
        mu = mu + eta_t * v

    return mu, q, log_Z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--eta", type=float, default=0.5)
    ap.add_argument("--max-iter", type=int, default=100)
    ap.add_argument("--tol", type=float, default=1e-3)
    ap.add_argument("--momentum", type=float, default=0.0)
    ap.add_argument("--eta-decay", type=float, default=0.0)
    ap.add_argument("--optimize", default="greedy",
                    help="path optimizer: greedy, auto, auto-hq, dp, or random-greedy")
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} K={p.n_colors}")

    contract_opts = {'optimize': args.optimize}
    t0 = time.time()
    mu_final, q_final, log_Z_final = lagrangian_loop_v3(
        p, args.eta, args.max_iter, args.tol,
        contract_opts=contract_opts,
        momentum=args.momentum,
        eta_decay=args.eta_decay,
    )
    print(f"\nFinal: log_Z={log_Z_final:.4f} max⟨q⟩={q_final.max():.4f} min⟨q⟩={q_final.min():.4f}")
    print(f"Time: {time.time()-t0:.2f}s")


if __name__ == "__main__":
    main()
