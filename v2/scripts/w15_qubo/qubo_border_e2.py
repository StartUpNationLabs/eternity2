"""W15 vol-124: QUBO encoder for the border-only sub-problem of canonical E2.

Builds the QUBO formulation for placing the 60 border pieces + 4 corner pieces
on the 60 perimeter cells of canonical E2. Uses one-hot encoding:
  x[piece_idx, rot, cell] = 1 if piece at that (rot, cell)

Variables:
  - For each corner cell (4): one binary per (corner_piece × valid_rot) ≈ 4 × 4 × 1 = 16
  - For each edge cell (56): one binary per (edge_piece × valid_rot) ≈ 56 × 56 × 1 = 3136
Total binary vars ≈ 3152 (fits Fixstars free tier 16k sparse).

Constraints (as penalty terms in QUBO):
  C1. Each border cell has exactly one piece placed: sum_{p,r} x[p,r,c] = 1
  C2. Each border piece appears in exactly one cell: sum_{c,r} x[p,r,c] = 1
  C3. Hint pieces forced: e.g., piece 138 at cell 135 with rot 0 (already pinned).
  C4. Internal border-edge color match between adjacent perimeter cells.

Objective:
  Maximize number of matched perimeter-adjacent edges (or equivalently
  minimize unmatched).
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

# Import puzzle loader from W1
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import Puzzle, load_puzzle, BORDER


W = 16
BORDER_POS = [r*W+c for r in range(W) for c in range(W) if r in (0, W-1) or c in (0, W-1)]
CORNER_POS = [0, W-1, W*(W-1), W*W-1]
EDGE_POS = [p for p in BORDER_POS if p not in CORNER_POS]


def classify_pieces(puzzle: Puzzle):
    """Return (corner_pids, edge_pids, interior_pids)."""
    corners, edges, interiors = [], [], []
    for pid in range(puzzle.n_pieces):
        # Use any rotation to count BORDER edges
        e0 = puzzle.piece_edges(pid, 0)
        n_border = sum(1 for c in e0 if c == BORDER)
        if n_border == 2:
            corners.append(pid)
        elif n_border == 1:
            edges.append(pid)
        else:
            interiors.append(pid)
    return corners, edges, interiors


def valid_rotations_for_cell(puzzle: Puzzle, pid: int, pos: int) -> list[int]:
    """List of rotations r such that placing piece pid with rotation r at pos
    has its BORDER edges facing outward (not into the board)."""
    row, col = pos // W, pos % W
    out = []
    for r in range(4):
        n, e, s, w = puzzle.piece_edges(pid, r)
        # For border cells, the "outside" sides must be BORDER (color 0).
        if row == 0 and n != BORDER: continue
        if row == W-1 and s != BORDER: continue
        if col == 0 and w != BORDER: continue
        if col == W-1 and e != BORDER: continue
        # And inside sides must NOT be BORDER (since adjacent is interior).
        if row != 0 and n == BORDER: continue
        if row != W-1 and s == BORDER: continue
        if col != 0 and w == BORDER: continue
        if col != W-1 and e == BORDER: continue
        out.append(r)
    return out


def build_var_index(puzzle: Puzzle):
    """Map (pid, rot, pos) → variable index. Only valid combos (border pieces
    on border cells with border-edge orientation) get vars."""
    corner_pids, edge_pids, _ = classify_pieces(puzzle)
    border_pieces = corner_pids + edge_pids  # 60 pieces

    var_idx = {}  # (pid, rot, pos) → idx
    pos_to_vars = {pos: [] for pos in BORDER_POS}
    piece_to_vars = {pid: [] for pid in border_pieces}

    for pid in border_pieces:
        for pos in BORDER_POS:
            for rot in valid_rotations_for_cell(puzzle, pid, pos):
                idx = len(var_idx)
                var_idx[(pid, rot, pos)] = idx
                pos_to_vars[pos].append(idx)
                piece_to_vars[pid].append(idx)

    return var_idx, pos_to_vars, piece_to_vars, border_pieces


def adjacent_border_pairs():
    """Return list of (pos_a, side_a, pos_b, side_b) for each adjacent pair on the perimeter.
    side encodes which side of pos_a faces pos_b. Side codes: 0=N, 1=E, 2=S, 3=W.
    Two positions are adjacent on the perimeter if they differ by (±1, 0) or (0, ±1)
    AND the line between them is on the perimeter ring.
    """
    pairs = []
    # Top row: (0,0)-(0,1)-...-(0,15): 15 pairs, side E from a to b
    for c in range(W-1):
        a = c; b = c+1
        pairs.append((a, 1, b, 3))  # a's E, b's W
    # Bottom row: similar
    for c in range(W-1):
        a = (W-1)*W + c; b = (W-1)*W + c + 1
        pairs.append((a, 1, b, 3))
    # Left column
    for r in range(W-1):
        a = r*W; b = (r+1)*W
        pairs.append((a, 2, b, 0))  # a's S, b's N
    # Right column
    for r in range(W-1):
        a = r*W + (W-1); b = (r+1)*W + (W-1)
        pairs.append((a, 2, b, 0))
    return pairs


def edge_color(puzzle: Puzzle, pid: int, rot: int, side: int) -> int:
    """Return color on a given side after rotation. side: 0=N, 1=E, 2=S, 3=W."""
    edges = puzzle.piece_edges(pid, rot)
    return edges[side]


def build_qubo(puzzle: Puzzle, lambda_cell: float = 10.0, lambda_piece: float = 10.0):
    """Build the QUBO model for the border-only problem.

    Returns (model, var_idx) — use amplify.solve(model, client) to solve.
    """
    from amplify import VariableGenerator, equal_to, one_hot

    var_idx, pos_to_vars, piece_to_vars, border_pieces = build_var_index(puzzle)
    n_vars = len(var_idx)
    print(f"[QUBO border] n_vars = {n_vars}")
    print(f"  pieces: {len(border_pieces)} | positions: {len(BORDER_POS)}")

    gen = VariableGenerator()
    x = gen.array("Binary", n_vars)

    # Build the inverse map for convenience
    idx_to_tuple = {v: k for k, v in var_idx.items()}

    # === Objective: maximize matched perimeter-adjacent border edges ===
    # For each adjacent border pair (a, side_a, b, side_b):
    #   reward = sum over (pid_a, rot_a) such that edge_color(pid_a, rot_a, side_a) = c
    #            and (pid_b, rot_b) with edge_color(pid_b, rot_b, side_b) = c
    #            of x[idx_a] * x[idx_b]
    # Maximize reward → minimize (-reward)

    pairs = adjacent_border_pairs()
    print(f"  perimeter pairs: {len(pairs)}")

    # Build per-pair color → matched-tuples lookup
    objective = 0
    n_terms = 0
    for (pos_a, side_a, pos_b, side_b) in pairs:
        # All vars at pos_a, group by (rotation-color on side_a)
        vars_a_by_color = {}
        for idx_a in pos_to_vars[pos_a]:
            (pid_a, rot_a, _) = idx_to_tuple[idx_a]
            c = edge_color(puzzle, pid_a, rot_a, side_a)
            if c == BORDER:
                continue  # border-side never matches across to interior, skip
            vars_a_by_color.setdefault(c, []).append(idx_a)
        vars_b_by_color = {}
        for idx_b in pos_to_vars[pos_b]:
            (pid_b, rot_b, _) = idx_to_tuple[idx_b]
            c = edge_color(puzzle, pid_b, rot_b, side_b)
            if c == BORDER:
                continue
            vars_b_by_color.setdefault(c, []).append(idx_b)
        for color in vars_a_by_color:
            if color not in vars_b_by_color:
                continue
            for idx_a in vars_a_by_color[color]:
                for idx_b in vars_b_by_color[color]:
                    objective -= x[idx_a] * x[idx_b]
                    n_terms += 1
    print(f"  objective terms: {n_terms}")

    # === Constraints (as penalties) ===
    # C1: each border position has exactly one piece
    cell_pen = 0
    for pos, vars_at_pos in pos_to_vars.items():
        if not vars_at_pos:
            continue
        s = sum(x[i] for i in vars_at_pos)
        cell_pen += (s - 1) ** 2
    # C2: each border piece appears exactly once
    piece_pen = 0
    for pid, vars_for_p in piece_to_vars.items():
        if not vars_for_p:
            continue
        s = sum(x[i] for i in vars_for_p)
        piece_pen += (s - 1) ** 2

    total_model = objective + lambda_cell * cell_pen + lambda_piece * piece_pen
    return total_model, x, var_idx, idx_to_tuple


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle",
                    default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--no-solve", action="store_true", help="build but don't submit")
    ap.add_argument("--token", default=None, help="Fixstars Amplify token (or set FIXSTARS_TOKEN env)")
    ap.add_argument("--time-ms", type=int, default=10000, help="solver time in milliseconds")
    args = ap.parse_args()

    puzzle = load_puzzle(Path(args.puzzle))
    print(f"Loaded puzzle: {puzzle.size}x{puzzle.size}, {puzzle.n_pieces} pieces, "
          f"{puzzle.n_colors} colors")

    model, x, var_idx, idx_to_tuple = build_qubo(puzzle)
    n_vars = len(var_idx)
    print(f"\nBuilt QUBO with {n_vars} binary variables")

    if args.no_solve:
        print("--no-solve: stopping after build")
        return

    import os
    token = args.token or os.environ.get("FIXSTARS_TOKEN")
    if not token:
        print("\n=== NO TOKEN ===")
        print("To submit, get a free token at https://amplify.fixstars.com/en/register")
        print("Then re-run with --token YOUR_TOKEN or set FIXSTARS_TOKEN env var.")
        return

    from amplify import FixstarsClient, solve
    client = FixstarsClient()
    client.token = token
    client.parameters.timeout = args.time_ms  # ms

    print(f"\nSubmitting to Fixstars Amplify AE (time_limit={args.time_ms} ms)...")
    result = solve(model, client)
    print(f"\nResult: {len(result)} feasible solutions")
    if len(result) > 0:
        best = result.best
        print(f"  Best objective: {best.objective}")
        vals = x.evaluate(best.values)
        # Decode: list active vars
        placements = []
        for idx, v in enumerate(vals):
            if v > 0.5:
                pid, rot, pos = idx_to_tuple[idx]
                placements.append({"pos": pos, "piece_id": pid, "rotation": rot})
        out_path = Path("output/vol-124/w15_qubo_border_result.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"placement": placements,
                                        "objective": float(best.objective)}, indent=2))
        print(f"  Wrote {out_path} ({len(placements)} cells placed)")
    else:
        print("  No feasible solutions found.")


if __name__ == "__main__":
    main()
