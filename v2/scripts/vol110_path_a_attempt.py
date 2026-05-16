#!/usr/bin/env python3
"""Vol-110 Path A attempt — subset σ-cycle + ALNS recovery.

For each σ-cycle between two 459 basins, apply ONLY that cycle to
basin_a (creating an intermediate board), save it. The intermediate
will have a score ≤ 459. Then run ALNS on each intermediate; the
question: can ALNS recover the lost edges AND gain +1 more?

Mathematical hope: a small σ-cycle introduces ~3-10 lost edges,
which ALNS can recover. If, while recovering, ALNS finds NEW
matches, the post-ALNS score could be 460+.

Usage: outputs intermediate JSON files for later ALNS runs.
"""

import csv
import json
import os
import sys
from pathlib import Path


def parse_color(s):
    s = s.strip()
    v = int(s, 2)
    if v == 65535:
        return 0
    return v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) < 4:
            continue
        try:
            t = parse_color(cols[0])
            r = parse_color(cols[1])
            b = parse_color(cols[2])
            l = parse_color(cols[3])
        except ValueError:
            continue
        pieces[pid] = (t, r, b, l)
        pid += 1
    return pieces


def rotate_edges(edges, rot):
    t, r, b, l = edges
    if rot == 0:
        return (t, r, b, l)
    elif rot == 1:
        return (l, t, r, b)
    elif rot == 2:
        return (b, l, t, r)
    else:
        return (r, b, l, t)


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def score_board(board, pieces, width=16, height=16):
    matched = 0
    placed = 0
    for y in range(height):
        for x in range(width):
            pos = y * width + x
            if pos not in board:
                continue
            placed += 1
            pid, rot = board[pos]
            if pid not in pieces:
                continue
            t, r, b, l = rotate_edges(pieces[pid], rot)
            if x + 1 < width:
                npos = pos + 1
                if npos in board:
                    npid, nrot = board[npos]
                    if npid in pieces:
                        nt, nr, nb, nl = rotate_edges(pieces[npid], nrot)
                        if r == nl and r != 0:
                            matched += 1
            if y + 1 < height:
                npos = pos + width
                if npos in board:
                    npid, nrot = board[npos]
                    if npid in pieces:
                        nt, nr, nb, nl = rotate_edges(pieces[npid], nrot)
                        if b == nt and b != 0:
                            matched += 1
    return matched, placed


def sigma_cycles(board_a, board_b):
    b_pos = {}
    for pos, (pid, _) in board_b.items():
        b_pos[pid] = pos
    sigma = {}
    for pos, (pid, _) in board_a.items():
        if pid in b_pos:
            sigma[pos] = b_pos[pid]
    seen = set()
    cycles = []
    for start in list(sigma.keys()):
        if start in seen:
            continue
        cyc = []
        q = start
        while q not in seen and q in sigma:
            seen.add(q)
            cyc.append(q)
            q = sigma[q]
        if len(cyc) >= 2:
            cycles.append(cyc)
    cycles.sort(key=lambda c: -len(c))
    return cycles


def save_board(board, path):
    """Save board dict in placement-array format."""
    pl = []
    for pos in sorted(board.keys()):
        pid, rot = board[pos]
        pl.append({"pos": pos, "piece_id": pid, "rotation": rot})
    out = {"placement": pl}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(out, f, indent=2)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("board_a")
    ap.add_argument("board_b")
    ap.add_argument("puzzle")
    ap.add_argument("out_dir")
    args = ap.parse_args()

    pieces = load_puzzle(args.puzzle)
    a = load_board(args.board_a)
    b = load_board(args.board_b)

    s_a, _ = score_board(a, pieces)
    s_b, _ = score_board(b, pieces)
    print(f"board_a: {s_a}/480")
    print(f"board_b: {s_b}/480")

    cycles = sigma_cycles(a, b)
    print(f"σ-cycles: {len(cycles)}, sizes={[len(c) for c in cycles]}")

    # For each cycle, generate the intermediate.
    for i, cyc in enumerate(cycles):
        intermediate = dict(a)
        for p in cyc:
            if p in b:
                intermediate[p] = b[p]
        s, _ = score_board(intermediate, pieces)
        out_path = f"{args.out_dir}/intermediate_cycle{i}_size{len(cyc)}_score{s}.json"
        save_board(intermediate, out_path)
        print(f"  cycle {i} (size {len(cyc)}): intermediate score={s}, saved {out_path}")


if __name__ == "__main__":
    main()
