#!/usr/bin/env python3
"""Apply iter-Hungarian to pairs of 460 basins (including the new ones).

If 459+459 → 460 worked, maybe 460+460 → 461."""

import json
import sys
from pathlib import Path
from itertools import combinations

import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
BORDER = 65535
W = 16


def load_pieces():
    import csv
    pieces = []
    with open(REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv") as f:
        reader = csv.reader(f); next(reader)
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
    pl = d.get("placement", [])
    if not pl: return None, 0
    return {p["pos"]: (p["piece_id"], p["rotation"]) for p in pl}, d.get("matched", 0)


def iterhung(board_a, board_b, pieces, max_iters=8):
    diff = sorted([pos for pos in range(256) if board_a.get(pos) != board_b.get(pos)])
    n = len(diff)
    if n == 0 or n > 60: return None, None, n
    pieces_a = [board_a[pos][0] for pos in diff if pos in board_a]
    pieces_b = [board_b[pos][0] for pos in diff if pos in board_b]
    union_pieces = sorted(set(pieces_a) | set(pieces_b))
    if len(union_pieces) != n: return None, None, n

    partial = {pos: d for pos, d in board_a.items() if pos not in set(diff)}
    current = dict(board_a)
    best_score = score_board(current, pieces)

    for it in range(max_iters):
        cost = np.zeros((n, n)); best_rot = np.zeros((n, n), dtype=np.int8)
        for ci, cell in enumerate(diff):
            ctx = {p: d for p, d in current.items() if p != cell}
            for pi, pid in enumerate(union_pieces):
                bm, br = -1, 0
                for r in range(4):
                    m = edges_at_pos(ctx, cell, pid, r, pieces)
                    if m > bm: bm, br = m, r
                cost[ci, pi] = -bm; best_rot[ci, pi] = br
        ri, ci_ = linear_sum_assignment(cost)
        new_placement = {diff[r]: (union_pieces[c], int(best_rot[r, c])) for r, c in zip(ri, ci_)}
        new_board = dict(partial); new_board.update(new_placement)
        new_score = score_board(new_board, pieces)
        if new_score > best_score:
            best_score = new_score; current = new_board
        else:
            break
    return current, best_score, n


def main():
    pieces = load_pieces()
    # Collect all 460 boards: existing + new.
    DB = REPO / "database-400-480"
    new460_dir = REPO / "output" / "vol-125" / "near_basin_hungarian_improvements"
    boards = []
    for f in DB.glob("460_*.json"):
        b, s = load_board(f)
        if b and len(b) == 256: boards.append((f.name, s, b))
    for f in new460_dir.glob("nh_pair*_score460.json"):
        b, s = load_board(f)
        if b and len(b) == 256: boards.append((f.name, s, b))
    print(f"Total 460 boards to pair: {len(boards)}", flush=True)

    if len(boards) < 2:
        sys.exit("need >= 2 boards")

    # Pairwise iter-Hungarian.
    improvements = []
    best_overall = 460
    best_board = None
    count = 0
    n_total = len(boards) * (len(boards) - 1) // 2

    for (na, sa, ba), (nb, sb, bb) in combinations(boards, 2):
        count += 1
        if count % 20 == 0:
            print(f"  {count}/{n_total} pairs tested", flush=True)
        new_b, new_s, n_diff = iterhung(ba, bb, pieces, max_iters=6)
        if new_s is None: continue
        if new_s > 460:
            print(f"🎯 {na[:30]} ↔ {nb[:30]} (n_diff={n_diff}): {new_s}!", flush=True)
            improvements.append((new_s, na, nb, new_b))
            if new_s > best_overall:
                best_overall = new_s
                best_board = new_b

    print(f"\n=== SUMMARY ===")
    print(f"Pairs tested: {count}")
    print(f"Improvements > 460: {len(improvements)}")
    print(f"Best: {best_overall}")

    if improvements:
        out_dir = REPO / "output" / "vol-125" / "iterhung_460_pairs"
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx, (sc, na, nb, board) in enumerate(sorted(improvements, key=lambda x: -x[0])):
            out = out_dir / f"iterhung460_{idx}_score{sc}.json"
            out.write_text(json.dumps({
                "matched": sc, "source": "iterhung_460_pairs",
                "pair_a": na, "pair_b": nb,
                "placement": [{"pos": p, "piece_id": pid, "rotation": rot}
                              for p, (pid, rot) in sorted(board.items())],
            }, indent=2))
        print(f"Saved {len(improvements)} improvements to {out_dir}")


if __name__ == "__main__":
    main()
