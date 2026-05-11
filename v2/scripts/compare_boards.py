#!/usr/bin/env python3
"""Compare two E2 plateau JSONs by border vs. interior similarity.

Usage:
    python3 compare_boards.py board_a.json board_b.json

Reports:
- Border cell agreement (60 cells, expected high if same basin).
- Interior cell agreement (196 cells).
- Mismatch overlap (do they share mismatched edges?).
"""

import json
import re
import sys

W = 16
H = 16


def parse_bucas(url):
    m = re.search(r'board_edges=([a-z]+)', url)
    if not m:
        return None
    blob = m.group(1)
    return [
        tuple(ord(blob[pos * 4 + i]) - ord('a') for i in range(4))
        for pos in range(W * H)
    ]


def is_border(pos):
    x, y = pos % W, pos // W
    return x == 0 or y == 0 or x == W - 1 or y == H - 1


def find_mismatches(quads):
    BORDER = 0
    out = set()
    for y in range(H):
        for x in range(W):
            pos = y * W + x
            (_, right, bottom, _) = quads[pos]
            if x + 1 < W:
                r = quads[pos + 1]
                me = right
                them = r[3]
                if me != BORDER and them != BORDER and me != them:
                    out.add(('h', pos))
            if y + 1 < H:
                b = quads[pos + W]
                me = bottom
                them = b[0]
                if me != BORDER and them != BORDER and me != them:
                    out.add(('v', pos))
    return out


def score(quads):
    matched = 0
    total = 0
    BORDER = 0
    for y in range(H):
        for x in range(W):
            pos = y * W + x
            (_, right, bottom, _) = quads[pos]
            if x + 1 < W:
                r = quads[pos + 1]
                if right != BORDER and r[3] != BORDER:
                    total += 1
                    if right == r[3]:
                        matched += 1
            if y + 1 < H:
                b = quads[pos + W]
                if bottom != BORDER and b[0] != BORDER:
                    total += 1
                    if bottom == b[0]:
                        matched += 1
    return matched, total


def main():
    if len(sys.argv) < 3:
        print("usage: compare_boards.py A.json B.json [more.json...]")
        sys.exit(1)
    paths = sys.argv[1:]
    boards = []
    for p in paths:
        with open(p) as f:
            j = json.load(f)
        q = parse_bucas(j["bucas_url"])
        if q is None:
            print(f"ERR: {p} has no bucas_url")
            continue
        s, t = score(q)
        m = find_mismatches(q)
        boards.append((p.split('/')[-1], q, s, t, m))

    print(f"{'file':<55} {'score':>5}  {'mismatches':>10}")
    for name, _, s, t, m in boards:
        print(f"{name:<55} {s}/{t}  {len(m):>10}")

    print()
    # Pairwise comparisons.
    for i in range(len(boards)):
        for j in range(i + 1, len(boards)):
            ni, qi, si, ti, mi = boards[i]
            nj, qj, sj, tj, mj = boards[j]
            border_diff = 0
            interior_diff = 0
            border_total = 0
            interior_total = 0
            for pos in range(W * H):
                if is_border(pos):
                    border_total += 1
                    if qi[pos] != qj[pos]:
                        border_diff += 1
                else:
                    interior_total += 1
                    if qi[pos] != qj[pos]:
                        interior_diff += 1
            shared_mis = len(mi & mj)
            print(f"\n{ni}\n  vs\n{nj}")
            print(f"  border:    {border_diff}/{border_total} cells differ ({100.0*border_diff/border_total:.0f}%)")
            print(f"  interior:  {interior_diff}/{interior_total} cells differ ({100.0*interior_diff/interior_total:.0f}%)")
            print(f"  shared mismatches: {shared_mis} (i={len(mi)}, j={len(mj)})")


if __name__ == "__main__":
    main()
