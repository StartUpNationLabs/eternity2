#!/usr/bin/env python3
"""Vol-122 prep — interior-only score on existing corpus.

Total adjacencies on 16×16: II=364, IB=56, BB=60, Sum=480.
Veteran milestone #3: complete internal 14×14 = all 364 I-I matched.

Usage:
    vol122_interior_only_score.py board1.json board2.json ... | directory
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

W, H = 16, 16


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                t = parse_color(cols[0])
                r = parse_color(cols[1])
                b = parse_color(cols[2])
                l = parse_color(cols[3])
                pieces[pid] = (t, r, b, l)
                pid += 1
            except ValueError:
                pass
    return pieces


def rotate(edges, rot):
    t, r, b, l = edges
    return [(t,r,b,l), (l,t,r,b), (b,l,t,r), (r,b,l,t)][rot]


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


def cell_class(pos):
    x, y = pos % W, pos // W
    if x in (0, W-1) and y in (0, H-1):
        return "corner"
    if x in (0, W-1) or y in (0, H-1):
        return "border"
    return "interior"


def score_by_class(board, pieces):
    ii = ib = bb = 0
    for pos, (pid, rot) in board.items():
        x, y = pos % W, pos // W
        e = rotate(pieces[pid], rot)
        cc = cell_class(pos)
        if x < W - 1 and (pos + 1) in board:
            npid, nrot = board[pos + 1]
            ne = rotate(pieces[npid], nrot)
            nc = cell_class(pos + 1)
            if e[1] == ne[3] and not (e[1] == 0 and ne[3] == 0):
                if cc == "interior" and nc == "interior":
                    ii += 1
                elif cc == "interior" or nc == "interior":
                    ib += 1
                else:
                    bb += 1
        if y < H - 1 and (pos + W) in board:
            npid, nrot = board[pos + W]
            ne = rotate(pieces[npid], nrot)
            nc = cell_class(pos + W)
            if e[2] == ne[0] and not (e[2] == 0 and ne[0] == 0):
                if cc == "interior" and nc == "interior":
                    ii += 1
                elif cc == "interior" or nc == "interior":
                    ib += 1
                else:
                    bb += 1
    return ii, ib, bb


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)
    pieces = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))

    print(f"# Total adjacencies: II=364, IB=56, BB=60, Sum=480")
    print(f"{'board':<60} {'II':>8} {'IB':>6} {'BB':>6} {'tot':>5}")
    rows = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            files = sorted(p.glob("*.json"))
        else:
            files = [p]
        for f in files:
            try:
                b = load_board(f)
                if len(b) < 200:
                    continue
                ii, ib, bb = score_by_class(b, pieces)
                rows.append((ii, ib, bb, f.name))
            except Exception as e:
                print(f"skip {f}: {e}", file=sys.stderr)
    rows.sort(reverse=True)
    for ii, ib, bb, name in rows:
        print(f"{name:<60} {ii:>4}/364 {ib:>3}/56 {bb:>3}/60 {ii+ib+bb:>3}/480")
    if rows:
        ii_max = max(r[0] for r in rows)
        ii_min = min(r[0] for r in rows)
        print(f"\n# II range: {ii_min} to {ii_max} / 364")
        print(f"# 14x14 milestone: II = 364 (none observed yet)")


if __name__ == "__main__":
    main()
