#!/usr/bin/env python3
"""V135-T1 — GRAIN polycrystalline E2 PoC.

Drop K seeds at random board positions. Each crystal grows greedily
by picking the best piece-rotation from shared inventory.
"""

from __future__ import annotations
import argparse, json, random, sys, time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_csv(p):
    BORDER_RAW = 65535
    pieces = []
    with open(p) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            sides = [int(s.strip(), 2) for s in parts[:4]]
            sides = [0 if v == BORDER_RAW else v for v in sides]
            pieces.append(tuple(sides))
    return size, pieces


def rotate_piece(p, r):
    n, e, s, w = p
    return [(n,e,s,w),(e,s,w,n),(s,w,n,e),(w,n,e,s)][r]


def piece_class(p):
    n = sum(1 for s in p if s == 0)
    return "corner" if n == 2 else ("edge" if n == 1 else "interior")


def required_class(pos, size):
    r, c = pos // size, pos % size
    is_corner = (r == 0 or r == size-1) and (c == 0 or c == size-1)
    is_border = r == 0 or r == size-1 or c == 0 or c == size-1
    return "corner" if is_corner else ("edge" if is_border else "interior")


def is_border_pos(pos, size):
    r, c = pos // size, pos % size
    return r == 0 or r == size-1 or c == 0 or c == size-1


def needed_zero_sides(pos, size):
    r, c = pos // size, pos % size
    sides = set()
    if r == 0: sides.add(0)
    if c == size - 1: sides.add(1)
    if r == size - 1: sides.add(2)
    if c == 0: sides.add(3)
    return sides


def neighbors(pos, size):
    r, c = pos // size, pos % size
    out = []
    if r > 0: out.append((pos - size, 0, 2))
    if c < size-1: out.append((pos + 1, 1, 3))
    if r < size-1: out.append((pos + size, 2, 0))
    if c > 0: out.append((pos - 1, 3, 1))
    return out


def count_matched_at(pos, piece_rotated, board, size):
    matches = 0
    for npos, my_side, their_side in neighbors(pos, size):
        if board[npos] is None: continue
        nside_color = board[npos][1][their_side]
        my_color = piece_rotated[my_side]
        if my_color == nside_color and my_color != 0:
            matches += 1
    return matches


def best_rotation_for_pos(piece, pos, size, board):
    needed_zeros = needed_zero_sides(pos, size)
    best = None
    best_matches = -1
    for r in range(4):
        rotated = rotate_piece(piece, r)
        if not all(rotated[s] == 0 for s in needed_zeros): continue
        ok = all(rotated[s] != 0 for s in range(4) if s not in needed_zeros)
        if not ok: continue
        matches = count_matched_at(pos, rotated, board, size)
        if matches > best_matches:
            best_matches = matches
            best = r
    if best is None: return None
    return (best, best_matches)


def grow_grain(size, pieces, n_crystals=4, seed=42):
    rng = random.Random(seed)
    n_cells = size * size
    inventory = set(range(len(pieces)))
    board = [None] * n_cells
    crystals = defaultdict(set)

    # Drop K seeds at random interior positions with interior pieces.
    interior_positions = [p for p in range(n_cells) if not is_border_pos(p, size)]
    if not interior_positions: return board, crystals
    seed_positions = rng.sample(interior_positions, min(n_crystals, len(interior_positions)))
    interior_pids = [p for p in range(len(pieces)) if piece_class(pieces[p]) == "interior"]

    for cid, spos in enumerate(seed_positions):
        available_interior = [p for p in interior_pids if p in inventory]
        if not available_interior: break
        pid = rng.choice(available_interior)
        r = rng.randint(0, 3)
        rotated = rotate_piece(pieces[pid], r)
        board[spos] = (pid, rotated, cid)
        crystals[cid].add(spos)
        inventory.discard(pid)

    n_placed = len(crystals)
    # Growth loop.
    iters = 0
    while n_placed < n_cells and inventory and iters < n_cells * 2:
        iters += 1
        progress = False
        for cid in list(crystals.keys()):
            bndry = set()
            for cpos in crystals[cid]:
                for npos, _, _ in neighbors(cpos, size):
                    if board[npos] is None: bndry.add(npos)
            if not bndry: continue
            best_choice = None
            best_score = -1
            for pos in bndry:
                rc = required_class(pos, size)
                for pid in inventory:
                    piece = pieces[pid]
                    if piece_class(piece) != rc: continue
                    res = best_rotation_for_pos(piece, pos, size, board)
                    if res is None: continue
                    r, matches = res
                    if matches > best_score:
                        best_score = matches
                        best_choice = (pos, pid, r)
            if best_choice is None:
                # Fallback: any valid placement.
                for pos in bndry:
                    rc = required_class(pos, size)
                    for pid in inventory:
                        piece = pieces[pid]
                        if piece_class(piece) != rc: continue
                        needed = needed_zero_sides(pos, size)
                        for r in range(4):
                            rotated = rotate_piece(piece, r)
                            if not all(rotated[s] == 0 for s in needed): continue
                            ok = all(rotated[s] != 0 for s in range(4) if s not in needed)
                            if not ok: continue
                            best_choice = (pos, pid, r); break
                        if best_choice: break
                    if best_choice: break
            if best_choice is None: continue
            pos, pid, r = best_choice
            rotated = rotate_piece(pieces[pid], r)
            board[pos] = (pid, rotated, cid)
            crystals[cid].add(pos)
            inventory.discard(pid)
            n_placed += 1
            progress = True
        if not progress: break

    # Fill remaining cells with any leftover piece.
    if n_placed < n_cells:
        for pos in range(n_cells):
            if board[pos] is not None: continue
            rc = required_class(pos, size)
            for pid in list(inventory):
                piece = pieces[pid]
                if piece_class(piece) != rc: continue
                needed = needed_zero_sides(pos, size)
                placed = False
                for r in range(4):
                    rotated = rotate_piece(piece, r)
                    if not all(rotated[s] == 0 for s in needed): continue
                    ok = all(rotated[s] != 0 for s in range(4) if s not in needed)
                    if not ok: continue
                    board[pos] = (pid, rotated, -1)
                    inventory.discard(pid)
                    n_placed += 1
                    placed = True
                    break
                if placed: break
    return board, crystals


def score_board_grain(board, size):
    matched = 0
    for r in range(size):
        for c in range(size):
            pos = r * size + c
            if board[pos] is None: continue
            rotated = board[pos][1]
            if c < size - 1:
                rpos = pos + 1
                if board[rpos] is not None:
                    if rotated[1] == board[rpos][1][3] and rotated[1] != 0:
                        matched += 1
            if r < size - 1:
                spos = pos + size
                if board[spos] is not None:
                    if rotated[2] == board[spos][1][0] and rotated[2] != 0:
                        matched += 1
    return matched


def total_interior_edges(size):
    return (size - 1) * size + size * (size - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--n-crystals", type=int, default=4)
    ap.add_argument("--seeds", type=str, default="42,1,7")
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    target = total_interior_edges(size)
    print(f"Puzzle: size={size}×{size} pieces={len(pieces)} target={target}", flush=True)
    for seed_s in args.seeds.split(","):
        seed = int(seed_s)
        t0 = time.time()
        board, crystals = grow_grain(size, pieces, args.n_crystals, seed)
        score = score_board_grain(board, size)
        n_placed = sum(1 for b in board if b is not None)
        elapsed = time.time() - t0
        print(f"  seed={seed} K={args.n_crystals}: score={score}/{target} "
              f"({score/target*100:.1f}%) placed={n_placed}/{size*size} "
              f"crystals={len(crystals)} t={elapsed:.1f}s", flush=True)


if __name__ == "__main__":
    main()
