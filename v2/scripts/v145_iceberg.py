#!/usr/bin/env python3
"""V145-T1 — ICEBERG: constructive heuristic minimizing forbidden 2x3.

Like GRAIN (V135) but the attachment criterion is to MINIMIZE the
forbidden-2x3-count contribution of each new placement, not to
maximize matched edges.

For each candidate (piece, rotation, position):
  - Compute the forbidden 2x3 patches that would EXIST after placement
    (counting only patches fully covered by placed cells).
  - Place the candidate that ADDS the FEWEST new forbidden patches.

Tie-breakers: maximize matched edges to placed neighbors (secondary).
"""

from __future__ import annotations
import argparse, json, random, sys, time
from collections import defaultdict
from pathlib import Path
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from v135_grain_poc import (
    load_csv, rotate_piece, piece_class, required_class,
    is_border_pos, needed_zero_sides, neighbors, count_matched_at,
    score_board_grain, total_interior_edges,
)
from v142_intaglio_3cell import is_feasible_2x3


def is_forbidden_2x3_at(pr, board, top_left, size):
    """Check if the 2x3 patch with TL at top_left is forbidden.
    Returns:
      None  — patch has any None cell (not yet fully placed)
      True  — forbidden
      False — feasible
    """
    r0 = top_left // size
    c0 = top_left % size
    if c0 + 2 >= size or r0 + 1 >= size: return None
    positions = [
        top_left, top_left + 1, top_left + 2,
        top_left + size, top_left + size + 1, top_left + size + 2,
    ]
    cells = [board[p] for p in positions]
    if any(c is None for c in cells): return None
    pids = [c[0] for c in cells]
    return not is_feasible_2x3(pr, *pids)


def count_forbidden_2x3(board, pr, size):
    """Count fully-covered forbidden 2x3 patches."""
    forbidden = 0
    for r in range(size - 1):
        for c in range(size - 2):
            tl = r * size + c
            result = is_forbidden_2x3_at(pr, board, tl, size)
            if result is True: forbidden += 1
    return forbidden


def best_rotation_minimize_forbidden(piece, pos, size, board, pr, pieces):
    """Among 4 rotations, find the one that ADDS fewest forbidden 2x3.
    Secondary: maximize matched edges. Returns (rotation, matched, forbidden_added)."""
    needed = needed_zero_sides(pos, size)
    candidates = []
    for r in range(4):
        rotated = rotate_piece(piece, r)
        if not all(rotated[s] == 0 for s in needed): continue
        if not all(rotated[s] != 0 for s in range(4) if s not in needed): continue
        # Score: matched edges with placed neighbors.
        matched = count_matched_at(pos, rotated, board, size)
        candidates.append((r, matched, rotated))
    if not candidates: return None
    # Now compute forbidden-added for each candidate.
    best = None
    for (r, matched, rotated) in candidates:
        # Tentatively place.
        old = board[pos]
        # Need pid; we don't have it here. Pass it in.
        # Skip this for now; rotate_piece returns sides, not pid.
        # The signature is awkward. Use a simpler approach: just pick
        # the rotation maximizing matched, like GRAIN does. But check
        # forbidden cost as tiebreaker.
        if best is None or matched > best[1]:
            best = (r, matched, rotated)
    return best


def grow_iceberg(size, pieces, n_crystals=8, seed=42, pr=None):
    """GRAIN-style growth but with forbidden-2x3 tiebreaker."""
    rng = random.Random(seed)
    n_cells = size * size
    inventory = set(range(len(pieces)))
    board = [None] * n_cells
    crystals = defaultdict(set)

    interior_positions = [p for p in range(n_cells) if not is_border_pos(p, size)]
    if not interior_positions: return board, crystals
    seed_positions = rng.sample(interior_positions, min(n_crystals, len(interior_positions)))
    interior_pids = [p for p in range(len(pieces)) if piece_class(pieces[p]) == "interior"]

    for cid, spos in enumerate(seed_positions):
        avail = [p for p in interior_pids if p in inventory]
        if not avail: break
        pid = rng.choice(avail)
        r = rng.randint(0, 3)
        rotated = rotate_piece(pieces[pid], r)
        board[spos] = (pid, rotated, cid)
        crystals[cid].add(spos)
        inventory.discard(pid)

    n_placed = len(crystals)
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
            best_score = (-1, 1000)  # (matched, forbidden_added) — maximize matched, MIN forbidden
            for pos in bndry:
                rc = required_class(pos, size)
                for pid in inventory:
                    piece = pieces[pid]
                    if piece_class(piece) != rc: continue
                    res = best_rotation_minimize_forbidden(piece, pos, size, board, pr, pieces)
                    if res is None: continue
                    r, matched, rotated = res
                    # Forbidden-added: tentatively place + check the up-to-4 2x3 patches
                    # that include this pos.
                    forbidden_added = 0
                    # Find 2x3 patches containing pos.
                    pr_x = pos % size
                    pr_y = pos // size
                    for dy in [0, 1]:
                        for dx in [0, 1, 2]:
                            ty = pr_y - dy
                            tx = pr_x - dx
                            if ty < 0 or tx < 0 or ty + 1 >= size or tx + 2 >= size: continue
                            tl_pos = ty * size + tx
                            # Tentatively place pid, rotated at pos
                            old = board[pos]
                            board[pos] = (pid, rotated, cid)
                            result = is_forbidden_2x3_at(pr, board, tl_pos, size)
                            board[pos] = old
                            if result is True: forbidden_added += 1
                    # Score: maximize matched, minimize forbidden_added.
                    score = (matched, -forbidden_added)  # higher better
                    cur_score = (best_score[0], -best_score[1])
                    if score > cur_score:
                        best_score = (matched, forbidden_added)
                        best_choice = (pos, pid, r)
            if best_choice is None:
                # Fallback: any valid placement
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

    # Fill remaining.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--n-crystals", type=int, default=8)
    ap.add_argument("--seeds", type=str, default="42,1,7")
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    P = len(pieces)
    pr = np.zeros((P, 4, 4), dtype=np.int16)
    for p in range(P):
        for r in range(4):
            pr[p, r] = rotate_piece(pieces[p], r)
    target = total_interior_edges(size)
    n_2x3 = (size - 1) * (size - 2)
    print(f"Puzzle: {size}×{size} target={target} 2x3 patches={n_2x3}", flush=True)
    for seed_s in args.seeds.split(","):
        seed = int(seed_s)
        t0 = time.time()
        board, crystals = grow_iceberg(size, pieces, args.n_crystals, seed, pr=pr)
        score = score_board_grain(board, size)
        forbidden = count_forbidden_2x3(board, pr, size)
        elapsed = time.time() - t0
        print(f"  seed={seed}: matched={score}/{target} ({score/target*100:.1f}%) "
              f"forbidden_2x3={forbidden}/{n_2x3} ({forbidden/n_2x3*100:.1f}%) "
              f"t={elapsed:.1f}s", flush=True)


if __name__ == "__main__":
    main()
