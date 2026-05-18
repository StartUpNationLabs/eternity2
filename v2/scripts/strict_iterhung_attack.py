#!/usr/bin/env python3
"""Strict-canonical iter-Hungarian attack on 458/457 boards.

The 5 canonical hint positions are FROZEN — they MUST remain at their
canonical (piece, rotation). The diff region excludes these.

This is the strict-canonical record-track. Current record: 458/480 with
all 5 hints obeyed. Attempt to find 459+ strict.
"""

import json
import sys
from pathlib import Path
from itertools import combinations
import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
DB = REPO / "database-400-480"
BORDER = 65535
W = 16

# Canonical 5-hint positions and required (piece, rotation).
CANONICAL = {135: (138, 0), 210: (180, 1), 34: (207, 1), 221: (248, 2), 45: (254, 1)}


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
    with open(path) as f: d = json.load(f)
    pl = d.get("placement", [])
    if not pl: return None, 0
    out = {}
    for i, p in enumerate(pl):
        if not isinstance(p, dict): continue
        pos = p.get("pos", i)
        if "piece_id" not in p or "rotation" not in p: return None, 0
        out[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    return out, d.get("matched", 0)

def is_strict_canonical(board):
    for pos, (exp_p, exp_r) in CANONICAL.items():
        if board.get(pos) != (exp_p, exp_r): return False
    return True

def iterhung_strict(board_a, board_b, pieces, max_iters=8):
    """iter-Hungarian where canonical hint cells are EXCLUDED from diff region."""
    diff = sorted([pos for pos in range(256)
                   if pos not in CANONICAL and board_a.get(pos) != board_b.get(pos)])
    n = len(diff)
    if n == 0 or n > 80: return None, None, n
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
        # Validate strict canonical still holds.
        if not is_strict_canonical(new_board):
            return None, None, n
        new_score = score_board(new_board, pieces)
        if new_score > best_score:
            best_score = new_score; current = new_board
        else: break
    return current, best_score, n


def main():
    pieces = load_pieces()
    # Find ALL strict-canonical boards in DB.
    strict_boards = []
    for f in sorted(DB.glob("*.json")):
        if f.name == "README.md": continue
        b, s = load_board(f)
        if b is None or len(b) != 256: continue
        if is_strict_canonical(b):
            strict_boards.append((f.name, s, b))
    strict_boards.sort(key=lambda x: -x[1])
    print(f"Found {len(strict_boards)} strict-canonical boards in DB", flush=True)
    print(f"Score distribution:")
    from collections import Counter
    cnt = Counter(s for _, s, _ in strict_boards)
    for sc in sorted(cnt, reverse=True):
        print(f"  {sc}: {cnt[sc]} boards", flush=True)

    if len(strict_boards) < 2:
        print(f"Need at least 2 strict-canonical boards for pairwise attack")
        return

    # Pairwise iter-Hungarian (strict variant).
    print(f"\n=== Strict iter-Hungarian on all pairs ===", flush=True)
    n = len(strict_boards)
    n_pairs = n * (n - 1) // 2
    print(f"  {n_pairs} pairs to test", flush=True)

    improvements = []
    best_overall = strict_boards[0][1]
    best_board = strict_boards[0][2]

    for (na, sa, ba), (nb, sb, bb) in combinations(strict_boards, 2):
        new_b, new_s, n_diff = iterhung_strict(ba, bb, pieces, max_iters=6)
        if new_s is None: continue
        target = max(sa, sb)
        if new_s > target:
            print(f"  🎯 {na[:30]} ({sa}) ↔ {nb[:30]} ({sb}) n_diff={n_diff} → {new_s}", flush=True)
            improvements.append((new_s, na, nb, n_diff, new_b))
            if new_s > best_overall:
                best_overall = new_s
                best_board = new_b

    print(f"\n=== SUMMARY ===")
    print(f"Improvements found: {len(improvements)}")
    print(f"Best strict-canonical score: {best_overall}")

    if improvements:
        out_dir = REPO / "output" / "vol-125" / "strict_iterhung_improvements"
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx, (sc, na, nb, n_diff, board) in enumerate(sorted(improvements, key=lambda x: -x[0])):
            out_path = out_dir / f"strict_iterhung_{idx}_score{sc}.json"
            out_path.write_text(json.dumps({
                "matched": sc, "source": "strict_iterhung_attack",
                "n_diff": n_diff,
                "pair_a": na, "pair_b": nb,
                "placement": [{"pos": p, "piece_id": pid, "rotation": rot}
                              for p, (pid, rot) in sorted(board.items())],
            }, indent=2))
        print(f"Saved to {out_dir}")
        if best_overall > 458:
            print(f"🎯🎯 STRICT RECORD BROKEN: 458 → {best_overall}")


if __name__ == "__main__":
    main()
