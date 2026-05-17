"""W15 main runner: build a QUBO for an edge-matching puzzle and solve it locally.

Solvers supported (all local, free):
  - neal (D-Wave dwave-neal simulated annealing)
  - sb (simulated-bifurcation, PyTorch, same algo as Toshiba SQBM+)

Usage:
  uv run python run_qubo.py --puzzle .../size_4_colors_4_e2d68b48.csv --solver neal --time 30
  uv run python run_qubo.py --puzzle .../size_6_colors_6_543a4a64.csv --solver sb --time 60
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from puzzle_loader import Puzzle, load_puzzle, BORDER
from qubo_full import build_qubo, decode, score


def amplify_to_qubo_dict(model):
    """Extract upper-triangular QUBO dict from amplify Poly or Model."""
    # build_qubo returns a Poly directly (not a Model), so use as_dict directly.
    if hasattr(model, "to_unconstrained_poly"):
        poly = model.to_unconstrained_poly().as_dict()
    else:
        poly = model.as_dict()
    qubo = {}
    constant = 0.0
    for key, coef in poly.items():
        if len(key) == 0:
            constant = float(coef)
        elif len(key) == 1:
            i = key[0]
            qubo[(i, i)] = qubo.get((i, i), 0) + float(coef)
        elif len(key) == 2:
            i, j = sorted(key)
            qubo[(i, j)] = qubo.get((i, j), 0) + float(coef)
        else:
            raise ValueError(f"Higher-order term: {key}")
    return qubo, constant


def solve_neal(model, n_vars, time_s, num_reads):
    import neal
    qubo, constant = amplify_to_qubo_dict(model)
    sampler = neal.SimulatedAnnealingSampler()
    t0 = time.time()
    result = sampler.sample_qubo(qubo, num_reads=num_reads)
    elapsed = time.time() - t0
    best = result.first
    sol = [int(best.sample.get(i, 0)) for i in range(n_vars)]
    print(f"  neal: {num_reads} reads in {elapsed:.1f}s, energy={best.energy + constant:.3f}")
    return sol, float(best.energy + constant)


def solve_sb(model, n_vars, time_s, mode="ballistic"):
    import torch
    import simulated_bifurcation as sb_lib
    qubo, constant = amplify_to_qubo_dict(model)
    Q = torch.zeros((n_vars, n_vars), dtype=torch.float32)
    for (i, j), v in qubo.items():
        Q[i, j] = v
        if i != j:
            Q[j, i] = v / 2  # symmetric
            Q[i, j] = v / 2
    # SB minimizes x^T Q x for x ∈ {0, 1}
    t0 = time.time()
    spins, value = sb_lib.minimize(Q, domain="binary", mode=mode,
                                    agents=50, max_steps=10000,
                                    timeout=time_s, best_only=True)
    elapsed = time.time() - t0
    # best_only=True returns 1-D tensors
    if spins.ndim == 1:
        sol = [int(s.item()) for s in spins]
    else:
        sol = [int(s.item()) for s in spins[0]]
    print(f"  SB ({mode}): {elapsed:.1f}s, value={float(value):.3f}")
    return sol, float(value)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--solver", default="neal", choices=["neal", "sb"])
    ap.add_argument("--time", type=float, default=30.0)
    ap.add_argument("--reads", type=int, default=100)
    ap.add_argument("--lambda-cell", type=float, default=50.0)
    ap.add_argument("--lambda-piece", type=float, default=50.0)
    ap.add_argument("--use-hints", action="store_true", help="enforce CSV hints")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    puzzle = load_puzzle(Path(args.puzzle))
    print(f"Puzzle: {puzzle.size}x{puzzle.size} ({puzzle.n_pieces} pieces, "
          f"{puzzle.n_colors} colors)")

    hints_dict = None
    if args.use_hints:
        # canonical E2 hints
        if puzzle.size == 16:
            hints_dict = {135: (138, 0), 210: (180, 1), 34: (207, 1),
                          221: (248, 2), 45: (254, 1)}

    model, x, var_idx, idx_to_tuple = build_qubo(
        puzzle, lambda_cell=args.lambda_cell, lambda_piece=args.lambda_piece,
        use_hints=args.use_hints, hints=hints_dict,
    )
    n_vars = len(var_idx)

    print(f"\nSolving with {args.solver} (time={args.time}s)...")
    if args.solver == "neal":
        sol, energy = solve_neal(model, n_vars, args.time, args.reads)
    else:
        sol, energy = solve_sb(model, n_vars, args.time)

    placements = decode(sol, idx_to_tuple, n_vars)
    sc = score(placements, puzzle)
    print(f"\nScore:")
    for k, v in sc.items():
        print(f"  {k}: {v}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "solver": args.solver,
            "n_vars": n_vars,
            "energy": energy,
            "placement": placements,
            "score": sc,
        }, indent=2))
        print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
