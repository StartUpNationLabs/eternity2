#!/usr/bin/env python3
"""Inspect the 4-cell difference between 469 (McGavin) and 466 (winning5 record).

These two boards differ in ONLY 4 cells. The 469 has higher score. The 466
has a different arrangement at those 4 cells. Question: is there a 5th
arrangement of those 4 cells that scores HIGHER than 469?

Test exhaustively: enumerate all (piece × rotation) over ALL 256 pieces
(not just the 4 in the diff) at those 4 cells, respecting piece-uniqueness
with the rest of the board.
"""

import json
import sys
from itertools import permutations
from pathlib import Path

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
DB = REPO / "database-400-480"
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


def main():
    # 469 (McGavin) and 466 (winning5)
    p_469 = DB / "469_mcgavin_469_6c9a2448.json"
    p_466 = DB / "466_winning5_sa_t1_s200_166766000_p55554_db75903a.json"
    board_469, _ = load_board(p_469)
    board_466, _ = load_board(p_466)
    pieces = load_pieces()
    s_469 = score_board(board_469, pieces)
    s_466 = score_board(board_466, pieces)
    print(f"469 rescored: {s_469}", flush=True)
    print(f"466 rescored: {s_466}", flush=True)

    diff_positions = sorted([pos for pos in range(256) if board_469.get(pos) != board_466.get(pos)])
    n = len(diff_positions)
    print(f"\nDiffering cells (n={n}):", flush=True)
    for pos in diff_positions:
        row, col = pos // W, pos % W
        a = board_469.get(pos)
        b = board_466.get(pos)
        print(f"  pos={pos} (row={row}, col={col})  469={a}  466={b}", flush=True)

    # Pieces at those cells in 469 (these are our pool).
    pool_469 = [board_469[pos][0] for pos in diff_positions]
    pool_466 = [board_466[pos][0] for pos in diff_positions]
    print(f"\n469 pieces at diff: {pool_469}", flush=True)
    print(f"466 pieces at diff: {pool_466}", flush=True)

    # Are these the same pieces, just rearranged?
    if set(pool_469) == set(pool_466):
        print(f"  → Same piece set; this is a SLOT-PERMUTATION between basins", flush=True)
    else:
        print(f"  → DIFFERENT piece sets: 469 has {set(pool_469) - set(pool_466)}, 466 has {set(pool_466) - set(pool_469)}", flush=True)

    # Full enumeration: permute the 4 pieces over 4 cells × 4^4 rotations.
    # For 469's pool only (we want to beat 469).
    rest = {pos: d for pos, d in board_469.items() if pos not in set(diff_positions)}
    print(f"\nExhaustive search: 4!=24 perms × 4^4=256 rotations = {24*256} configs", flush=True)
    best = s_469
    best_config = None
    for perm in permutations(pool_469):
        # 4^n rotation combinations.
        for rot_bits in range(4 ** n):
            rotations = []
            r = rot_bits
            for _ in range(n):
                rotations.append(r % 4); r //= 4
            new_board = dict(rest)
            for idx, pos in enumerate(diff_positions):
                new_board[pos] = (perm[idx], rotations[idx])
            sc = score_board(new_board, pieces)
            if sc > best:
                best = sc
                best_config = (perm, tuple(rotations))
    print(f"\nBest score in full enumeration: {best}", flush=True)
    if best > s_469:
        print(f"🎯🎯 BEAT 469: new score {best}!", flush=True)
        print(f"  perm: {best_config[0]}", flush=True)
        print(f"  rots: {best_config[1]}", flush=True)
    else:
        print(f"No improvement past {s_469}.", flush=True)

    # Also try 466's pool (different pieces).
    if set(pool_469) != set(pool_466):
        print(f"\n--- Also trying 466's piece pool over 469's other cells ---", flush=True)
        # Need to swap 469's pieces at diff with 466's pieces. Some pieces in
        # 466's pool may already be in 469's rest. Skip those (would create duplicates).
        rest_469_pieces = set(pid for pid, _ in rest.values())
        bad_466_pieces = set(pool_466) & rest_469_pieces
        if bad_466_pieces:
            print(f"  Cannot use 466's pool directly: pieces {bad_466_pieces} already in 469's rest", flush=True)
            return
        for perm in permutations(pool_466):
            for rot_bits in range(4 ** n):
                rotations = []
                r = rot_bits
                for _ in range(n):
                    rotations.append(r % 4); r //= 4
                new_board = dict(rest)
                for idx, pos in enumerate(diff_positions):
                    new_board[pos] = (perm[idx], rotations[idx])
                sc = score_board(new_board, pieces)
                if sc > best:
                    best = sc
                    best_config = (perm, tuple(rotations))
        print(f"  Best with 466 pool: {best}", flush=True)


if __name__ == "__main__":
    main()
