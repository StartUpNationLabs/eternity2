"""W15 local-simulator runner: convert the Amplify model to a BQM and solve
locally via dwave-neal (simulated annealing) or simulated-bifurcation (SB).

This is the SAME algorithm as Toshiba's SQBM+ — Pytorch implementation of
Simulated Bifurcation. So we can prototype free on the user's machine before
deciding whether to pay for the commercial Azure/Fixstars cloud version.

Usage:
  uv run --project scripts/w15_qubo python scripts/w15_qubo/solve_local_sim.py [--solver neal|sb] [--border-only] [--time 60]
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import Puzzle, load_puzzle, BORDER

from qubo_border_e2 import (
    build_qubo as build_border_qubo,
    classify_pieces, BORDER_POS, CORNER_POS, EDGE_POS, W,
    valid_rotations_for_cell, adjacent_border_pairs, edge_color,
)


def amplify_to_bqm(model, x):
    """Convert an amplify model + binary array into a dict-of-dicts BQM that
    dwave-neal can sample from."""
    from amplify import to_qubo
    # Amplify v1.5 exposes to_qubo / .as_qubo on Poly objects.
    # The function returns a tuple (qubo_matrix, constant) where qubo_matrix is
    # an upper-triangular dict {(i,j): coef}.
    qubo_dict, constant = to_qubo(model)
    return qubo_dict, constant


def amplify_to_torch_ising(model, x):
    """Convert amplify QUBO to a torch ising matrix for simulated-bifurcation."""
    import torch
    qubo_dict, _ = amplify_to_bqm(model, x)
    n_vars = len(x)
    # Find max idx
    max_idx = 0
    for (i, j) in qubo_dict.keys():
        max_idx = max(max_idx, i, j)
    n = max_idx + 1
    Q = torch.zeros((n, n), dtype=torch.float32)
    for (i, j), v in qubo_dict.items():
        Q[i, j] = v
        if i != j:
            Q[j, i] = v
    return Q


def solve_with_neal(model, x, time_limit_s: float = 60.0, num_reads: int = 100):
    """Use dwave-neal simulated annealing."""
    import neal
    qubo_dict, constant = amplify_to_bqm(model, x)
    print(f"  QUBO terms: {len(qubo_dict)}, constant: {constant:.2f}")

    sampler = neal.SimulatedAnnealingSampler()
    t0 = time.time()
    result = sampler.sample_qubo(qubo_dict, num_reads=num_reads)
    elapsed = time.time() - t0
    best = result.first
    print(f"  neal: {num_reads} reads in {elapsed:.1f}s")
    print(f"  best energy: {best.energy + constant:.3f}")
    # Convert sample dict to list (idx → 0/1)
    n_vars = len(x)
    sol = [int(best.sample.get(i, 0)) for i in range(n_vars)]
    return sol, best.energy + constant


def solve_with_sb(model, x, time_limit_s: float = 60.0, mode: str = "bSB"):
    """Use simulated-bifurcation. mode in {bSB, dSB, ballistic, discrete}."""
    import torch
    import simulated_bifurcation as sb
    Q = amplify_to_torch_ising(model, x)
    n = Q.shape[0]
    print(f"  SB matrix: {n}×{n} (will minimize x^T Q x for binary x)")

    t0 = time.time()
    # `optimize` directly on QUBO with domain="binary"
    spins, value = sb.optimize(
        Q, mode=mode,
        domain="binary",
        agents=100,           # parallel agents
        max_steps=10000,
        timeout=time_limit_s,
    )
    elapsed = time.time() - t0
    print(f"  SB ({mode}): elapsed {elapsed:.1f}s, value={value:.3f}")
    return spins.cpu().tolist(), float(value)


def decode_border_solution(sol, x, idx_to_tuple, puzzle: Puzzle, n_vars: int):
    """Decode the active vars into a placement list."""
    placements = []
    for idx in range(n_vars):
        if sol[idx] > 0.5:
            pid, rot, pos = idx_to_tuple[idx]
            placements.append({"pos": pos, "piece_id": pid, "rotation": rot})
    return placements


def score_border(placements, puzzle: Puzzle):
    """Score a border placement: count cell-position uniqueness, piece-uniqueness,
    and matched perimeter-adjacent edges."""
    # Cell uniqueness
    cells = {}
    for p in placements:
        cells.setdefault(p["pos"], []).append(p)
    duplicate_cells = {pos: ps for pos, ps in cells.items() if len(ps) > 1}
    empty_cells = [pos for pos in BORDER_POS if pos not in cells]
    # Piece uniqueness
    pieces_used = {}
    for p in placements:
        pieces_used.setdefault(p["piece_id"], []).append(p)
    duplicate_pieces = {pid: ps for pid, ps in pieces_used.items() if len(ps) > 1}

    # Border-adjacent matches
    pos_to_piece = {p["pos"]: p for p in placements}
    pairs = adjacent_border_pairs()
    matched = 0
    total = 0
    for (a, sa, b, sb_) in pairs:
        if a not in pos_to_piece or b not in pos_to_piece:
            continue
        pa = pos_to_piece[a]; pb = pos_to_piece[b]
        ca = edge_color(puzzle, pa["piece_id"], pa["rotation"], sa)
        cb = edge_color(puzzle, pb["piece_id"], pb["rotation"], sb_)
        if ca == BORDER or cb == BORDER:
            continue  # don't score border-side
        if ca == cb:
            matched += 1
        total += 1

    return {
        "n_placements": len(placements),
        "empty_cells": len(empty_cells),
        "duplicate_cells": len(duplicate_cells),
        "duplicate_pieces": len(duplicate_pieces),
        "matched_perimeter_edges": matched,
        "total_perimeter_edges": total,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--solver", choices=["neal", "sb-bSB", "sb-dSB"], default="neal")
    ap.add_argument("--time", type=float, default=30.0)
    ap.add_argument("--reads", type=int, default=100, help="num_reads for neal")
    ap.add_argument("--lambda-cell", type=float, default=10.0)
    ap.add_argument("--lambda-piece", type=float, default=10.0)
    ap.add_argument("--out", default="output/vol-124/w15_local_sim_result.json")
    args = ap.parse_args()

    puzzle = load_puzzle(Path(args.puzzle))
    print(f"Loaded puzzle: {puzzle.size}x{puzzle.size}, {puzzle.n_pieces} pieces, {puzzle.n_colors} colors")
    print(f"\nBuilding border-only QUBO (λ_cell={args.lambda_cell}, λ_piece={args.lambda_piece})...")
    model, x, var_idx, idx_to_tuple = build_border_qubo(
        puzzle, lambda_cell=args.lambda_cell, lambda_piece=args.lambda_piece
    )
    n_vars = len(var_idx)
    print(f"  {n_vars} binary vars")

    print(f"\nSolving with {args.solver} (time={args.time}s)...")
    if args.solver == "neal":
        sol, energy = solve_with_neal(model, x, args.time, args.reads)
    else:
        mode = args.solver.split("-")[1]
        sol, energy = solve_with_sb(model, x, args.time, mode=mode)

    placements = decode_border_solution(sol, x, idx_to_tuple, puzzle, n_vars)
    print(f"\nDecoded {len(placements)} active vars")

    score = score_border(placements, puzzle)
    print(f"Score:")
    for k, v in score.items():
        print(f"  {k}: {v}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "solver": args.solver,
        "n_vars": n_vars,
        "energy": energy,
        "placement": placements,
        "score": score,
    }, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
