#!/usr/bin/env python3
"""Vol-122 — K=1 move lock analysis of standing 459 record.

For the verified 459 basin (vol-60 RECORD_TIE_459_p06):
- Test ALL 256 × 4 = 1024 in-place piece rotations.
- Test all 256C2 × 4 × 4 = ~520k piece-swap-with-rotation.
- Count how many moves yield Δ ≥ 0 (potential improvements).

Goal: empirically confirm K=1 lock (per memory rigidity theorem).
"""

from __future__ import annotations
import json
import sys
from pathlib import Path


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v

def load_pieces():
    pieces = {}
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces[pid] = tuple(parse_color(cols[i]) for i in range(4))
                pid += 1
            except ValueError: pass
    return pieces

def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def main():
    board_path = Path(sys.argv[1] if len(sys.argv) > 1 else "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json")
    pieces = load_pieces()
    side = 16

    with open(board_path) as f:
        d = json.load(f)
    placed = {}
    for e in d.get('placement', []):
        if e is None: continue
        placed[e['pos']] = (e['piece_id'], e['rotation'])
    print(f"loaded: {len(placed)} placed cells from {board_path.name}")

    def score(board):
        """Count matched internal edges."""
        total = 0
        for r in range(side):
            for c in range(side):
                pos = r * side + c
                if pos not in board: continue
                pid, rot = board[pos]
                edges = rotate(pieces[pid], rot)
                # Right neighbor
                if c < side - 1:
                    npos = pos + 1
                    if npos in board:
                        npid, nrot = board[npos]
                        nedges = rotate(pieces[npid], nrot)
                        if edges[1] == nedges[3] and edges[1] != 0:
                            total += 1
                # Bottom neighbor
                if r < side - 1:
                    npos = pos + side
                    if npos in board:
                        npid, nrot = board[npos]
                        nedges = rotate(pieces[npid], nrot)
                        if edges[2] == nedges[0] and edges[2] != 0:
                            total += 1
        return total

    base_score = score(placed)
    print(f"base score: {base_score}")

    # K=1: in-place rotation
    print("\n=== K=1 in-place rotation moves ===")
    n_improving = 0
    n_neutral = 0
    n_worse = 0
    for pos in placed:
        pid, rot = placed[pos]
        for new_rot in range(4):
            if new_rot == rot: continue
            placed[pos] = (pid, new_rot)
            s = score(placed)
            d = s - base_score
            if d > 0: n_improving += 1
            elif d == 0: n_neutral += 1
            else: n_worse += 1
            placed[pos] = (pid, rot)  # restore
    total = n_improving + n_neutral + n_worse
    print(f"  total moves tested: {total}")
    print(f"  Δ > 0 (improvements): {n_improving}")
    print(f"  Δ == 0 (neutral): {n_neutral}")
    print(f"  Δ < 0 (worse): {n_worse}")
    if n_improving == 0:
        print(f"  ✓ CONFIRMED LOCKED under K=1 in-place rotation")

    # K=2: swap pieces (no rotation)
    print("\n=== K=2 piece swap (no rotation change) ===")
    positions = list(placed.keys())
    n_improving = 0
    n_neutral = 0
    n_worse = 0
    n_tested = 0
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            p1, p2 = positions[i], positions[j]
            placed[p1], placed[p2] = placed[p2], placed[p1]
            s = score(placed)
            d = s - base_score
            n_tested += 1
            if d > 0: n_improving += 1
            elif d == 0: n_neutral += 1
            else: n_worse += 1
            placed[p1], placed[p2] = placed[p2], placed[p1]
    print(f"  total swaps tested: {n_tested}")
    print(f"  Δ > 0 (improvements): {n_improving}")
    print(f"  Δ == 0 (neutral): {n_neutral}")
    print(f"  Δ < 0 (worse): {n_worse}")
    if n_improving == 0:
        print(f"  ✓ CONFIRMED LOCKED under K=2 simple swap (no-rotation)")


if __name__ == "__main__":
    main()
