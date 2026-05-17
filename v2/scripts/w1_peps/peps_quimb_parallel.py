"""W1 — Parallel version of peps_quimb_lagrangian using multiprocessing.

The per-cell opened-tensor contractions are embarrassingly parallel. We use
multiprocessing.Pool to distribute them across cores. Expected speedup:
~Ncores (typically 8-10x).

This is a drop-in replacement for the serial version's compute_Z_open_per_cell.

Note: each subprocess re-imports quimb and builds the TN. The first call may
be slow; subsequent are fast.
"""
from __future__ import annotations
import argparse
import sys
import time
import multiprocessing as mp
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER

# Module-level globals set by the worker initializer (one per process).
_g_puzzle: Optional[Puzzle] = None
_g_lookup = None


def _init_worker(puzzle_path: str):
    """Worker process initializer — load puzzle once per process."""
    global _g_puzzle, _g_lookup
    from peps_quimb_lagrangian import build_piece_signature_lookup
    _g_puzzle = load_puzzle(puzzle_path)
    _g_lookup = build_piece_signature_lookup(_g_puzzle)


def _contract_open_cell(args):
    """Worker function: contract the PEPS with one cell removed."""
    global _g_puzzle, _g_lookup
    skip, mu_list, pinned_serialized, chi = args
    import quimb.tensor as qtn
    from peps_quimb_lagrangian import build_quimb_2d_tn

    p = _g_puzzle
    mu = np.asarray(mu_list)
    # pinned_serialized is dict-like with int keys and (pid, rot) values
    pinned = {int(k): (int(v[0]), int(v[1])) for k, v in pinned_serialized.items()} if pinned_serialized else None
    tn = build_quimb_2d_tn(p, mu, pinned=pinned, skip_cell=skip)
    y, x = skip // p.size, skip % p.size
    out_inds = []
    if y > 0: out_inds.append(f'v_{y-1}_{x}')
    if x < p.size - 1: out_inds.append(f'h_{y}_{x}')
    if y < p.size - 1: out_inds.append(f'v_{y}_{x}')
    if x > 0: out_inds.append(f'h_{y}_{x-1}')
    # Use 'greedy' optimizer in workers (no nested parallelism)
    result = tn.contract(output_inds=out_inds, optimize='greedy')
    if isinstance(result, qtn.Tensor):
        arr = result.transpose(*out_inds).data
    else:
        arr = np.asarray(result)
    return skip, arr


def compute_Z_open_parallel(
    puzzle_path: str,
    puzzle: Puzzle,
    mu: np.ndarray,
    chi: int,
    pinned: dict[int, tuple[int, int]] | None,
    pool: mp.Pool,
) -> dict[int, np.ndarray]:
    """Parallel version of compute_Z_open_per_cell."""
    size = puzzle.size
    pinned = pinned or {}
    pinned_serialized = {k: list(v) for k, v in pinned.items()}
    mu_list = mu.tolist()
    skip_list = [i for i in range(size * size) if i not in pinned]
    args_list = [(skip, mu_list, pinned_serialized, chi) for skip in skip_list]
    results = pool.map(_contract_open_cell, args_list)
    return dict(results)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("--chi", type=int, default=64)
    ap.add_argument("--eta", type=float, default=0.3)
    ap.add_argument("--max-iter", type=int, default=80)
    ap.add_argument("--tol", type=float, default=0.05)
    ap.add_argument("--max-fixes", type=int, default=None)
    ap.add_argument("--nproc", type=int, default=mp.cpu_count())
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Puzzle: size={p.size} pieces={p.n_pieces} K={p.n_colors}")
    print(f"Using {args.nproc} processes")

    from peps_quimb_lagrangian import (
        compute_log_Z,
        find_most_peaked_cell,
        build_piece_signature_lookup,
    )

    # Bootstrap pool
    print(f"Starting worker pool...", flush=True)
    pool = mp.Pool(
        processes=args.nproc,
        initializer=_init_worker,
        initargs=(args.puzzle,),
    )

    pinned: dict[int, tuple[int, int]] = {}
    n_cells = p.size * p.size
    max_to_fix = args.max_fixes or n_cells

    t_start = time.time()

    try:
        while len(pinned) < max_to_fix and len(pinned) < n_cells:
            print(f"\n=== round {len(pinned)+1}/{max_to_fix} ===", flush=True)
            mu = np.zeros(p.n_pieces)
            v = np.zeros_like(mu)
            log_Z = -np.inf
            Z_open: dict = {}
            q = np.zeros(p.n_pieces)

            for it in range(args.max_iter):
                log_Z = compute_log_Z(p, mu, args.chi, pinned)
                if not np.isfinite(log_Z):
                    print(f"  iter {it}: log_Z = -inf; aborting round", flush=True)
                    break
                Z_open = compute_Z_open_parallel(args.puzzle, p, mu, args.chi, pinned, pool)
                # Compute q
                Z_full = float(np.exp(log_Z))
                q = np.zeros(p.n_pieces)
                for pos, (pid, _) in pinned.items():
                    q[pid] += 1.0
                for i, Zi in Z_open.items():
                    y, x = i // p.size, i % p.size
                    n_b = y == 0
                    e_b = x == p.size - 1
                    s_b = y == p.size - 1
                    w_b = x == 0
                    for pid in range(p.n_pieces):
                        if any(pp == pid for pp, _ in pinned.values()): continue
                        for rot in range(4):
                            sig = p.piece_edges(pid, rot)
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
                                Z_open_val = float(Zi)
                            else:
                                Z_open_val = float(Zi[tuple(idx)])
                            contrib = np.exp(-mu[pid]) * Z_open_val / Z_full
                            q[pid] += contrib
                gap_inf = float(np.max(np.abs(q - 1.0)))
                elapsed = time.time() - t_start
                if it < 10 or it % 5 == 0:
                    print(f"  it {it:3d}: logZ={log_Z:.4f}  |q-1|∞={gap_inf:.5f}  "
                          f"max(q)={q.max():.3f}  t={elapsed:.1f}s", flush=True)
                if gap_inf < args.tol:
                    print(f"  converged at it={it}, |q-1|∞={gap_inf:.5f}", flush=True)
                    break
                v_new = args.eta * (q - 1.0)
                mu = mu + v_new

            # Find most peaked
            best = find_most_peaked_cell(p, Z_open, mu, log_Z, pinned)
            if best is None:
                print("  no candidate, stopping", flush=True)
                break
            cell, pid, rot, prob = best
            y, x = cell // p.size, cell % p.size
            print(f"  fix cell ({y},{x}) → piece={pid} rot={rot}  prob={prob:.4f}", flush=True)
            pinned[cell] = (pid, rot)

        elapsed = time.time() - t_start
        print(f"\nFinal: {len(pinned)} cells fixed in {elapsed:.1f}s")
        for pos in range(p.size * p.size):
            if pos in pinned:
                pid, rot = pinned[pos]
                y, x = pos // p.size, pos % p.size
                print(f"  cell ({y},{x}): piece={pid} rot={rot}")

    finally:
        pool.close()
        pool.join()


if __name__ == "__main__":
    main()
