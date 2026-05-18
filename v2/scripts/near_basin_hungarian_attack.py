#!/usr/bin/env python3
"""Near-basin Hungarian attack: for each near-pair (A, B) in DB, identify
the differing cells D and the union of pieces used at D in either basin.

Then formulate a bipartite assignment: D × pieces_union × rotations.
Solve Hungarian for the OPTIMAL static assignment (max edge-matches with
fixed boundary).

This is exhaustive over rotations per cell (4 rots × |D| cells) and uses
Hungarian for the permutation step. Tractable up to diff ~ 50.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
BORDER = 65535
W = 16


def load_pieces():
    import csv
    pieces = []
    with open(REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            N, E, S, W_ = (int(row[i].strip(), 2) for i in range(4))
            pieces.append((N, E, S, W_))
    return pieces


def rotate(piece, r):
    N, E, S, W_ = piece
    if r == 0: return (N, E, S, W_)
    if r == 1: return (W_, N, E, S)
    if r == 2: return (S, W_, N, E)
    if r == 3: return (E, S, W_, N)


def edges_at_pos(board, pos, piece_id, rot, pieces):
    row, col = pos // W, pos % W
    p_edges = rotate(pieces[piece_id], rot)
    matches = 0
    for d_pos, opp, mine in [(-W, 2, 0), (+W, 0, 2), (-1, 1, 3), (+1, 3, 1)]:
        if d_pos == -W and row == 0: continue
        if d_pos == +W and row == 15: continue
        if d_pos == -1 and col == 0: continue
        if d_pos == +1 and col == 15: continue
        nb_pos = pos + d_pos
        if nb_pos in board:
            nb_pid, nb_rot = board[nb_pos]
            nb_edges = rotate(pieces[nb_pid], nb_rot)
            if nb_edges[opp] == p_edges[mine] and p_edges[mine] != BORDER:
                matches += 1
    return matches


def score_board(board, pieces):
    matches = 0
    for pos, (pid, rot) in board.items():
        row, col = pos // W, pos % W
        p_edges = rotate(pieces[pid], rot)
        if col < 15 and (pos + 1) in board:
            nb = board[pos + 1]; ne = rotate(pieces[nb[0]], nb[1])
            if p_edges[1] == ne[3] and p_edges[1] != BORDER: matches += 1
        if row < 15 and (pos + W) in board:
            nb = board[pos + W]; ne = rotate(pieces[nb[0]], nb[1])
            if p_edges[2] == ne[0] and p_edges[2] != BORDER: matches += 1
    return matches


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    return {p["pos"]: (p["piece_id"], p["rotation"]) for p in d["placement"]}, d.get("matched", 0)


def iterhung_local(board_a, board_b, pieces, max_iters=8):
    """For the differing region, run iterative Hungarian."""
    diff = sorted([pos for pos in range(256) if board_a.get(pos) != board_b.get(pos)])
    n = len(diff)
    if n == 0: return board_a, score_board(board_a, pieces), n
    pieces_a = [board_a[pos][0] for pos in diff]
    pieces_b = [board_b[pos][0] for pos in diff if pos in board_b]
    union_pieces = sorted(set(pieces_a) | set(pieces_b))
    # The pieces NOT in A's pool must displace something. We can only proceed
    # if union size == n (each piece occupies one diff cell).
    if len(union_pieces) > n:
        # More pieces than slots — need to also fix some non-diff cells.
        # For simplicity skip these (rare in our diff<20 pairs).
        return None, None, n
    # Pad with extras? Actually if union < n, we have <n pieces for n cells — infeasible.
    if len(union_pieces) < n:
        return None, None, n

    partial = {pos: d for pos, d in board_a.items() if pos not in set(diff)}
    # Initial: A's assignment.
    current = dict(board_a)
    best_score = score_board(current, pieces)

    for it in range(max_iters):
        # Compute cost matrix |D| × |union_pieces|.
        cost = np.zeros((n, n))
        best_rot = np.zeros((n, n), dtype=np.int8)
        for ci, cell in enumerate(diff):
            ctx = {p: d for p, d in current.items() if p != cell}
            for pi, pid in enumerate(union_pieces):
                bm, br = -1, 0
                for r in range(4):
                    m = edges_at_pos(ctx, cell, pid, r, pieces)
                    if m > bm: bm, br = m, r
                cost[ci, pi] = -bm
                best_rot[ci, pi] = br
        ri, ci_ = linear_sum_assignment(cost)
        new_placement = {diff[r]: (union_pieces[c], int(best_rot[r, c])) for r, c in zip(ri, ci_)}
        new_board = dict(partial)
        new_board.update(new_placement)
        new_score = score_board(new_board, pieces)
        if new_score > best_score:
            best_score = new_score
            current = new_board
        else:
            break

    return current, best_score, n


def main():
    pairs_path = REPO / "output" / "vol-125" / "near_basins" / "near_pairs.json"
    pairs = json.loads(pairs_path.read_text())
    pieces = load_pieces()
    DB = REPO / "database-400-480"

    print(f"Near-pair Hungarian attack — {len(pairs)} pairs", flush=True)

    best_overall = 0
    best_board = None
    improvements = []

    for pair_idx, pair in enumerate(pairs):
        if pair["diff"] == 0 or pair["diff"] > 60: continue
        try:
            ba, _ = load_board(DB / pair["name_a"])
            bb, _ = load_board(DB / pair["name_b"])
        except Exception:
            continue
        s_a = score_board(ba, pieces)
        s_b = score_board(bb, pieces)
        new_board, new_score, n = iterhung_local(ba, bb, pieces, max_iters=6)
        if new_score is None: continue
        improved = new_score > max(s_a, s_b)
        marker = " 🎯" if improved else ""
        if improved or pair_idx < 30:
            print(f"  pair {pair_idx:3d} (n_diff={n:3d}): A={s_a}, B={s_b}, iterHung={new_score}{marker}", flush=True)
        if improved:
            improvements.append((new_score, pair_idx, pair, new_board))
        if new_score > best_overall:
            best_overall = new_score
            best_board = new_board

    print(f"\n=== SUMMARY ===")
    print(f"Total improvements found: {len(improvements)}")
    print(f"Best score overall: {best_overall}")

    if improvements:
        print(f"\nTop 5 improvements:")
        for sc, idx, pair, _ in sorted(improvements, key=lambda x: -x[0])[:5]:
            print(f"  pair {idx}: {pair['name_a'][:30]} ({pair['score_a']}) ↔ {pair['name_b'][:30]} ({pair['score_b']}) → {sc}")

    if best_overall > 0 and best_board:
        out_path = REPO / "output" / "vol-125" / f"near_basin_hungarian_{best_overall}.json"
        out_data = {
            "matched": best_overall,
            "source": "near_basin_hungarian_attack",
            "placement": [
                {"pos": p, "piece_id": pid, "rotation": rot}
                for p, (pid, rot) in sorted(best_board.items())
            ],
        }
        out_path.write_text(json.dumps(out_data, indent=2))
        print(f"\nSaved best board to {out_path}")

    # Also save every improvement individually for DB integration.
    out_dir = REPO / "output" / "vol-125" / "near_basin_hungarian_improvements"
    out_dir.mkdir(parents=True, exist_ok=True)
    for sc, idx, pair, board in improvements:
        out_path = out_dir / f"nh_pair{idx}_score{sc}.json"
        out_data = {
            "matched": sc,
            "source": "near_basin_hungarian",
            "source_pair_idx": idx,
            "source_pair_a": pair["name_a"],
            "source_pair_b": pair["name_b"],
            "placement": [
                {"pos": p, "piece_id": pid, "rotation": rot}
                for p, (pid, rot) in sorted(board.items())
            ],
        }
        out_path.write_text(json.dumps(out_data, indent=2))
    print(f"Saved {len(improvements)} improvements to {out_dir}")


if __name__ == "__main__":
    main()
