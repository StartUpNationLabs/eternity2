#!/usr/bin/env python3
"""iter-Hungarian on high-score pairs (461+461, 461+460, 469+469, etc.)"""

import json, sys
from pathlib import Path
from itertools import combinations, product
import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
BORDER = 65535; W = 16

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


def iterhung(board_a, board_b, pieces, max_iters=8):
    diff = sorted([pos for pos in range(256) if board_a.get(pos) != board_b.get(pos)])
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
        new_score = score_board(new_board, pieces)
        if new_score > best_score:
            best_score = new_score; current = new_board
        else: break
    return current, best_score, n


def main():
    pieces = load_pieces()
    DB = REPO / "database-400-480"
    new460_dir = REPO / "output" / "vol-125" / "near_basin_hungarian_improvements"

    # Collect boards by score-band.
    bands = {461: [], 460: [], 459: [], 458: [], 469: []}
    for score_filter in bands:
        for f in DB.glob(f"{score_filter}_*.json"):
            b, s = load_board(f)
            if b and len(b) == 256 and s == score_filter:
                bands[s].append((f.name, b))
    # Also include new boards.
    for f in new460_dir.glob("nh_pair*_score460.json"):
        b, s = load_board(f)
        if b and len(b) == 256: bands[460].append((f.name, b))
    for sc, ls in bands.items():
        print(f"{sc}: {len(ls)} boards", flush=True)

    # Try pairs: 461×461, 461×460, 461×469, 469×469
    pair_groups = [
        ("461x461", bands[461], bands[461]),
        ("461x460", bands[461], bands[460]),
        ("461x469", bands[461], bands[469]),
        ("469x469", bands[469], bands[469]),
        ("461x459", bands[461], bands[459]),
        ("460x459", bands[460], bands[459]),
    ]
    out_dir = REPO / "output" / "vol-125" / "iterhung_high_improvements"
    out_dir.mkdir(parents=True, exist_ok=True)
    best_overall = 0
    total_improvements = 0

    for group_name, lhs, rhs in pair_groups:
        if not lhs or not rhs: continue
        # Avoid self-pair, dedup.
        seen = set()
        pairs = []
        for (na, ba), (nb, bb) in product(lhs, rhs):
            if na == nb: continue
            key = tuple(sorted([na, nb]))
            if key in seen: continue
            seen.add(key)
            pairs.append((na, ba, nb, bb))
        print(f"\n[{group_name}] {len(pairs)} pairs to test", flush=True)
        improvements = []
        for idx, (na, ba, nb, bb) in enumerate(pairs):
            sa = score_board(ba, pieces); sb = score_board(bb, pieces)
            new_b, new_s, n_diff = iterhung(ba, bb, pieces, max_iters=8)
            if new_s is None: continue
            target = max(sa, sb)
            if new_s > target:
                print(f"  🎯 {na[:30]} ({sa}) ↔ {nb[:30]} ({sb}) (n_diff={n_diff}): {new_s}", flush=True)
                improvements.append((new_s, na, nb, n_diff, new_b))
                if new_s > best_overall:
                    best_overall = new_s
        print(f"  {len(improvements)} improvements found in {group_name}", flush=True)
        for idx, (sc, na, nb, n_diff, board) in enumerate(improvements):
            out_path = out_dir / f"{group_name}_idx{idx}_score{sc}.json"
            out_path.write_text(json.dumps({
                "matched": sc, "source": f"iterhung_{group_name}",
                "n_diff": n_diff,
                "pair_a": na, "pair_b": nb,
                "placement": [{"pos": p, "piece_id": pid, "rotation": rot}
                              for p, (pid, rot) in sorted(board.items())],
            }, indent=2))
        total_improvements += len(improvements)

    print(f"\n=== TOTAL ===")
    print(f"Total improvements: {total_improvements}")
    print(f"Best score: {best_overall}")


if __name__ == "__main__":
    main()
