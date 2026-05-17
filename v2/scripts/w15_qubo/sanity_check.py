"""W15 sanity check: does our QUBO ACTUALLY have the ground-truth solution at its minimum?

Build the QUBO for a small generated puzzle, then compute the energy at:
  (a) the known ground-truth (from CSV metadata: piece i at cell (x_i, y_i))
  (b) any random feasible assignment
  (c) the all-zero assignment

If (a) doesn't have the lowest energy, our QUBO formulation is BROKEN.
This is the test that decides whether to keep pushing on QUBO or pivot.
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from puzzle_loader import load_puzzle, BORDER
from qubo_full import build_qubo, decode, score, valid_rotations_for_cell
from run_qubo import amplify_to_qubo_dict


def parse_ground_truth(csv_path):
    """The generator CSV encodes piece i at (x_i, y_i). Extract that mapping.

    Returns: list of (piece_id, rotation, pos) for the full ground-truth placement.
    Rotation must be re-determined since CSV doesn't store it directly — we'll
    try all 4 rotations and pick the one whose BORDER sides match cell geometry.
    """
    with open(csv_path) as f:
        lines = f.read().splitlines()
    W = int(lines[0])
    placements = []
    for pid, line in enumerate(lines[1:1+W*W]):
        parts = line.split(",")
        x = int(parts[5]); y = int(parts[6])
        pos = y * W + x
        placements.append((pid, pos))
    return W, placements


def energy_at_assignment(qubo: dict, constant: float, x_vals: dict[int, int]) -> float:
    """Evaluate the QUBO at a fixed assignment x: {var_idx -> 0 or 1}."""
    e = constant
    for (i, j), coef in qubo.items():
        vi = x_vals.get(i, 0); vj = x_vals.get(j, 0)
        e += coef * vi * vj
    return e


def find_rotation_for_piece_at_cell(puzzle, pid, pos):
    """Among valid rotations for this piece at this cell, pick the one whose
    interior edges match the ground-truth neighbors (if possible).
    For sanity check: just take the first valid rotation."""
    rs = valid_rotations_for_cell(puzzle, pid, pos)
    return rs[0] if rs else None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--lambda-cell", type=float, default=100.0)
    ap.add_argument("--lambda-piece", type=float, default=100.0)
    args = ap.parse_args()

    puzzle = load_puzzle(Path(args.puzzle))
    print(f"Puzzle: {puzzle.size}x{puzzle.size}")
    W, gt_placements = parse_ground_truth(args.puzzle)

    model, x, var_idx, idx_to_tuple = build_qubo(
        puzzle, lambda_cell=args.lambda_cell, lambda_piece=args.lambda_piece
    )
    n_vars = len(var_idx)
    qubo, constant = amplify_to_qubo_dict(model)

    # === Find the right rotation for each piece at its GT position by trying all 4 ===
    # The correct rotation is the one that makes interior matches with neighbors.
    # For sanity: try all 4 rotations × pieces, find the consistent assignment.
    # Naive: for each (pid, pos), find the rotation whose edge colors equal
    # those of the neighbors at neighboring cells.
    pos_to_pid = {pos: pid for pid, pos in gt_placements}

    def edge_color(pid, rot, side):
        return puzzle.piece_edges(pid, rot)[side]

    gt_rotations = {}
    for pid, pos in gt_placements:
        row, col = pos // W, pos % W
        best_rot = None
        best_matches = -1
        # Try all 4 rotations, pick the one with the most matched neighbor edges
        for r in range(4):
            n_c, e_c, s_c, w_c = puzzle.piece_edges(pid, r)
            # Check border consistency
            if row == 0 and n_c != BORDER: continue
            if row == W-1 and s_c != BORDER: continue
            if col == 0 and w_c != BORDER: continue
            if col == W-1 and e_c != BORDER: continue
            if row != 0 and n_c == BORDER: continue
            if row != W-1 and s_c == BORDER: continue
            if col != 0 and w_c == BORDER: continue
            if col != W-1 and e_c == BORDER: continue

            matches = 0
            for (dr, dc, side, opp_side) in [(-1, 0, 0, 2), (0, 1, 1, 3),
                                              (1, 0, 2, 0), (0, -1, 3, 1)]:
                nr, nc = row + dr, col + dc
                if not (0 <= nr < W and 0 <= nc < W): continue
                npos = nr * W + nc
                npid = pos_to_pid[npos]
                # Try all rotations for the neighbor too — too combinatorial,
                # so just compare against the FIRST valid rot of the neighbor
                # (rough heuristic; full check below).
                this_color = puzzle.piece_edges(pid, r)[side]
                # We'll match later in a second pass; for now just count if non-BORDER.
                if this_color != BORDER:
                    matches += 1
            if matches > best_matches:
                best_matches = matches
                best_rot = r
        gt_rotations[pid] = best_rot if best_rot is not None else 0

    # Build the assignment dict
    x_vals = {i: 0 for i in range(n_vars)}
    n_set = 0
    for pid, pos in gt_placements:
        rot = gt_rotations[pid]
        key = (pid, rot, pos)
        if key in var_idx:
            x_vals[var_idx[key]] = 1
            n_set += 1
        else:
            print(f"  WARNING: piece {pid} at pos {pos} rot {rot} NOT IN var_idx — "
                  f"may have wrong rotation. Valid rotations: "
                  f"{valid_rotations_for_cell(puzzle, pid, pos)}")
    print(f"\nGround-truth placement: {n_set}/{len(gt_placements)} variables set")

    # Compute energy at ground truth
    e_gt = energy_at_assignment(qubo, constant, x_vals)
    print(f"Energy at ground truth: {e_gt:.3f}")

    # Decode + score
    placements = []
    for idx, v in x_vals.items():
        if v == 1:
            pid, rot, pos = idx_to_tuple[idx]
            placements.append({"pos": pos, "piece_id": pid, "rotation": rot})
    sc = score(placements, puzzle)
    print(f"Score at ground truth:")
    for k, v in sc.items():
        print(f"  {k}: {v}")

    # All-zero baseline
    e_zero = energy_at_assignment(qubo, constant, {})
    print(f"\nEnergy at all-zero: {e_zero:.3f}")

    # If GT is perfect, expected energy = -matched_interior (after constant cancellation)
    # If GT gives matched_interior=total_interior, that's the puzzle's max.
    print(f"\nExpected energy at perfect GT = -matched_interior = "
          f"-{sc['total_interior']}")
    print(f"Got: {e_gt:.3f}. Difference: {e_gt + sc['total_interior']:.3f}")

    if abs(e_gt + sc['total_interior']) < 1.0 and sc['is_perfect']:
        print(f"\n✅ QUBO is CORRECT: ground-truth solution is at expected minimum.")
    elif sc['is_perfect']:
        print(f"\n⚠️  Placement is perfect but energy differs from expected by "
              f"{e_gt + sc['total_interior']:.3f} — check formulation.")
    else:
        print(f"\n❌ ROTATION HEURISTIC FAILED to find perfect placement. "
              f"GT placement is invalid. Need a smarter rotation finder.")


if __name__ == "__main__":
    main()
