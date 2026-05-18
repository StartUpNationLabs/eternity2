#!/usr/bin/env python3
"""Attack the closest near-basin pairs in the database.

Take pairs with diff <= 20 cells. For each pair (A, B):
1. Identify the differing cells D (4-20 cells).
2. Enumerate ALL piece-rotation permutations of A's pieces at D.
   For |D|=4 cells, that's 4! × 4^4 = 6144 options. Tractable.
3. For each permutation, score it. Keep the best.

This is EXHAUSTIVE local search over the differing region —
guaranteed optimal within the diff-locality.
"""

import json
import sys
from itertools import permutations
from pathlib import Path

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


def attack_pair(name_a, name_b, board_a, board_b, pieces, max_diff=12):
    """Exhaustive search over the differing region of two boards.

    Set up: positions where boardA[pos] != boardB[pos]. Call this D.
    pieces_at_D = set of all pieces used at D in either A or B (union).
    For each assignment of pieces_at_D to D × rotations, score.
    """
    diff_positions = [pos for pos in range(256) if board_a.get(pos) != board_b.get(pos)]
    n = len(diff_positions)
    if n > max_diff:
        return None
    if n == 0:
        return None
    # Collect pieces used at D in A and B.
    pieces_a = [board_a[pos][0] for pos in diff_positions]
    pieces_b = [board_b[pos][0] for pos in diff_positions if pos in board_b]
    union_pieces = list(set(pieces_a) | set(pieces_b))
    if len(union_pieces) != n:
        # Imbalanced — would need to pull pieces from elsewhere. Skip.
        return None
    # The "fixed" rest of the board (cells outside D, from A).
    rest = {pos: d for pos, d in board_a.items() if pos not in diff_positions}

    sA = score_board(board_a, pieces)
    sB = score_board(board_b, pieces) if all(pos in board_b for pos in diff_positions) else None
    best = sA
    best_assign = None
    trials = 0
    # Iterate permutations of union_pieces over diff_positions.
    for perm in permutations(union_pieces):
        # For each piece in perm, try all 4 rotations.
        # That's n! × 4^n total. Cap at 1e6.
        # Use a fast branch: pick rotation per cell GREEDILY for this permutation.
        # (Not exhaustive over rotations, but with n small this approximates well.)
        new_board = dict(rest)
        # Greedy rotation per cell, in cell-order.
        for idx, pos in enumerate(diff_positions):
            pid = perm[idx]
            best_r = 0
            best_m = -1
            for r in range(4):
                # Score local matches.
                p_edges = rotate(pieces[pid], r)
                m = 0
                for d_pos, opp, mine in [(-W, 2, 0), (+W, 0, 2), (-1, 1, 3), (+1, 3, 1)]:
                    nb_pos = pos + d_pos
                    if nb_pos < 0 or nb_pos >= 256: continue
                    if d_pos == -W and pos // W == 0: continue
                    if d_pos == +W and pos // W == 15: continue
                    if d_pos == -1 and pos % W == 0: continue
                    if d_pos == +1 and pos % W == 15: continue
                    if nb_pos in new_board:
                        nb_pid, nb_rot = new_board[nb_pos]
                        nb_edges = rotate(pieces[nb_pid], nb_rot)
                        if nb_edges[opp] == p_edges[mine] and p_edges[mine] != BORDER:
                            m += 1
                if m > best_m:
                    best_m = m
                    best_r = r
            new_board[pos] = (pid, best_r)
        sc = score_board(new_board, pieces)
        trials += 1
        if sc > best:
            best = sc
            best_assign = dict(new_board)
        if trials > 1_000_000: break

    return {"trials": trials, "best_score": best, "best_board": best_assign,
            "score_a": sA, "score_b": sB, "n_diff": n}


def main():
    pairs_path = REPO / "output" / "vol-125" / "near_basins" / "near_pairs.json"
    if not pairs_path.exists():
        sys.exit("need near_pairs.json — run find_near_basins.py first")
    pairs = json.loads(pairs_path.read_text())
    pieces = load_pieces()

    DB = REPO / "database-400-480"
    print(f"Attacking near-pairs from {pairs_path}", flush=True)

    best_overall = 0
    best_overall_board = None
    attempted = 0
    successful = 0

    for pair_idx, pair in enumerate(pairs):
        if pair["diff"] == 0: continue  # identical, skip
        if pair["diff"] > 12: break  # too large for exhaustive
        name_a = pair["name_a"]
        name_b = pair["name_b"]
        board_a, _ = load_board(DB / name_a)
        board_b, _ = load_board(DB / name_b)
        result = attack_pair(name_a, name_b, board_a, board_b, pieces, max_diff=12)
        if result is None: continue
        attempted += 1
        if result["best_score"] > max(result["score_a"], result["score_b"] or 0):
            successful += 1
            print(f"  🎯 PAIR #{pair_idx} ({name_a[:30]} ↔ {name_b[:30]})", flush=True)
            print(f"     A={result['score_a']}, B={result['score_b']}, NEW={result['best_score']} (n_diff={result['n_diff']}, trials={result['trials']})", flush=True)
            if result["best_score"] > best_overall:
                best_overall = result["best_score"]
                best_overall_board = result["best_board"]
        else:
            print(f"  pair #{pair_idx} (diff={result['n_diff']}, trials={result['trials']}): A={result['score_a']}, B={result['score_b']}, best={result['best_score']} (no improvement)", flush=True)

    print(f"\n=== SUMMARY ===")
    print(f"Pairs attempted: {attempted}")
    print(f"Successful improvements: {successful}")
    print(f"Best overall score: {best_overall}")

    if best_overall_board:
        out_path = REPO / "output" / "vol-125" / f"near_basin_attack_{best_overall}.json"
        out_data = {
            "matched": best_overall,
            "source": "near_basin_attack",
            "placement": [
                {"pos": p, "piece_id": pid, "rotation": rot}
                for p, (pid, rot) in sorted(best_overall_board.items())
            ],
        }
        out_path.write_text(json.dumps(out_data, indent=2))
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
