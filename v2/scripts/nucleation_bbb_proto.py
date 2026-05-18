#!/usr/bin/env python3
"""NUCLEATION BB&B prototype — Seifer-inspired BFS-grown search.

Instead of MRV (smallest-domain-first), start from a SEED cell and grow
outward in BFS order. This explores a DIFFERENT subtree than DFS-MRV,
potentially breaking out of the depth-40 plateau.

Seed choices:
- The 5 canonical hints (frozen, placed first)
- Hint-adjacent cells next (BFS distance 1 from any hint)
- Etc.

Repair: simple greedy per-cell (best-of-rotation per piece, max edge matches).
This is a STRAW-MAN to see if nucleation order alone makes a difference.
"""

import json
import sys
import csv
from collections import deque
from pathlib import Path

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
BORDER = 65535
W = 16

CANONICAL = {135: (138, 0), 210: (180, 1), 34: (207, 1), 221: (248, 2), 45: (254, 1)}


def load_pieces():
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


def best_rotation_local(board, pos, piece_id, pieces):
    """Return (matches, rotation) where matches max over rotations."""
    row, col = pos // W, pos % W
    p = pieces[piece_id]
    best_m, best_r = -1, 0
    for r in range(4):
        e = rotate(p, r)
        m = 0
        # Check 4 neighbors
        # N
        if row > 0 and (pos - W) in board:
            nb = board[pos - W]; ne = rotate(pieces[nb[0]], nb[1])
            if e[0] == ne[2] and e[0] != BORDER: m += 1
        elif row == 0 and e[0] == BORDER:
            pass  # border match doesn't count toward score
        # E
        if col < 15 and (pos + 1) in board:
            nb = board[pos + 1]; ne = rotate(pieces[nb[0]], nb[1])
            if e[1] == ne[3] and e[1] != BORDER: m += 1
        # S
        if row < 15 and (pos + W) in board:
            nb = board[pos + W]; ne = rotate(pieces[nb[0]], nb[1])
            if e[2] == ne[0] and e[2] != BORDER: m += 1
        # W
        if col > 0 and (pos - 1) in board:
            nb = board[pos - 1]; ne = rotate(pieces[nb[0]], nb[1])
            if e[3] == ne[1] and e[3] != BORDER: m += 1
        if m > best_m:
            best_m, best_r = m, r
    return best_m, best_r


def score_board(board, pieces):
    matches = 0
    for pos, (pid, rot) in board.items():
        row, col = pos // W, pos % W
        e = rotate(pieces[pid], rot)
        if col < 15 and (pos + 1) in board:
            nb = board[pos + 1]; ne = rotate(pieces[nb[0]], nb[1])
            if e[1] == ne[3] and e[1] != BORDER: matches += 1
        if row < 15 and (pos + W) in board:
            nb = board[pos + W]; ne = rotate(pieces[nb[0]], nb[1])
            if e[2] == ne[0] and e[2] != BORDER: matches += 1
    return matches


def nucleation(pieces, seed_positions, used_pieces_at_seed):
    """Greedy nucleation: start with seeds, BFS outward, picking best-match
    piece+rotation at each step. Returns final board + score."""
    board = dict(seed_positions)  # already-placed cells
    used = set(used_pieces_at_seed)
    # BFS frontier from seed cells.
    visited = set(board.keys())
    frontier = deque()
    for pos in board:
        for d in [-W, +W, -1, +1]:
            nb_pos = pos + d
            if d == -W and pos // W == 0: continue
            if d == +W and pos // W == 15: continue
            if d == -1 and pos % W == 0: continue
            if d == +1 and pos % W == 15: continue
            if nb_pos not in visited:
                visited.add(nb_pos)
                frontier.append(nb_pos)

    while frontier:
        pos = frontier.popleft()
        if pos in board:
            continue
        # Find best piece for this cell.
        best_pid, best_rot, best_score = None, 0, -1
        for pid in range(256):
            if pid in used: continue
            m, r = best_rotation_local(board, pos, pid, pieces)
            if m > best_score:
                best_score, best_pid, best_rot = m, pid, r
        if best_pid is None:
            # Should not happen unless used == all
            break
        board[pos] = (best_pid, best_rot)
        used.add(best_pid)
        # Extend frontier.
        for d in [-W, +W, -1, +1]:
            nb_pos = pos + d
            if d == -W and pos // W == 0: continue
            if d == +W and pos // W == 15: continue
            if d == -1 and pos % W == 0: continue
            if d == +1 and pos % W == 15: continue
            if nb_pos not in visited:
                visited.add(nb_pos)
                frontier.append(nb_pos)
    return board, score_board(board, pieces)


def main():
    pieces = load_pieces()

    # Start with canonical 5 hints as seeds.
    print(f"=== Nucleation from canonical hints ===", flush=True)
    seeds = dict(CANONICAL)
    used = {pid for pid, _ in seeds.values()}
    board, score = nucleation(pieces, seeds, used)
    print(f"  hint-seed result: score = {score}", flush=True)

    # Try seeding from just the TOP-LEFT corner instead.
    print(f"\n=== Nucleation from a single corner seed ===", flush=True)
    # The top-left piece is pid=0 in canonical Selby-Riordan.
    seeds_corner = {0: (0, 0)}  # pos 0 = piece 0, rotation 0
    used_corner = {0}
    board, score = nucleation(pieces, seeds_corner, used_corner)
    print(f"  corner-seed result: score = {score}", flush=True)

    # Try seeding from 1 hint at a time.
    print(f"\n=== Nucleation from each single hint ===", flush=True)
    best_single_hint_score = 0
    best_single_hint_board = None
    for pos, (pid, rot) in CANONICAL.items():
        seeds = {pos: (pid, rot)}
        used = {pid}
        board, score = nucleation(pieces, seeds, used)
        print(f"  seed pos={pos} piece={pid}: score = {score}", flush=True)
        if score > best_single_hint_score:
            best_single_hint_score = score
            best_single_hint_board = board

    print(f"\nBest single-hint nucleation: {best_single_hint_score}", flush=True)


if __name__ == "__main__":
    main()
