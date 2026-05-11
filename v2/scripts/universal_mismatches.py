#!/usr/bin/env python3
"""Find structurally-hard mismatch positions across many plateau JSONs.

A "universal mismatch" is an interior edge that fails to match in a
large fraction of our PT-converged boards. These are candidates for
genuinely-structural defects that no local-search method can fix.

Usage:
    python3 universal_mismatches.py [--min-score N] [--threshold-frac F]

Globs all output/*.json (alns_e2, pt_e2, frame_first_e2, edge_cp_e2).
"""

import argparse
import glob
import json
import re
from collections import Counter

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


def find_mismatches(quads):
    BORDER = 0
    out = []
    for y in range(H):
        for x in range(W):
            pos = y * W + x
            (_, right, bottom, _) = quads[pos]
            if x + 1 < W:
                r = quads[pos + 1]
                if right != BORDER and r[3] != BORDER and right != r[3]:
                    out.append(('h', pos))
            if y + 1 < H:
                b = quads[pos + W]
                if bottom != BORDER and b[0] != BORDER and bottom != b[0]:
                    out.append(('v', pos))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=int, default=400,
                    help="Ignore boards with overall score below this (default 400)")
    ap.add_argument("--threshold-frac", type=float, default=0.5,
                    help="Report mismatches appearing in this fraction of boards (default 0.5)")
    ap.add_argument("--top", type=int, default=30,
                    help="Show top-N most frequent mismatches (default 30)")
    args = ap.parse_args()

    freq = Counter()
    boards_analyzed = 0
    score_distribution = []
    for pattern in [
        "output/pt_e2_*.json",
        "output/frame_first_e2_*.json",
        "output/alns_e2_*of480.json",
        "output/edge_cp_e2_*.json",
    ]:
        for path in sorted(glob.glob(pattern)):
            with open(path) as f:
                j = json.load(f)
            url = j.get("bucas_url", "")
            if not url:
                continue
            q = parse_bucas(url)
            if not q:
                continue
            score = j.get("score", {}).get("matched_edges", 0)
            if score < args.min_score:
                continue
            boards_analyzed += 1
            score_distribution.append(score)
            for m in find_mismatches(q):
                freq[m] += 1

    print(f"boards analyzed (score >= {args.min_score}): {boards_analyzed}")
    if boards_analyzed:
        score_distribution.sort()
        print(f"score range: {score_distribution[0]} .. {score_distribution[-1]}")
        print(f"score median: {score_distribution[len(score_distribution)//2]}")
    print(f"distinct mismatch positions: {len(freq)}")
    if not freq:
        return
    print(f"max frequency: {max(freq.values())}")

    print(f"\nTop-{args.top} most frequent mismatches:")
    print(f"{'freq':>4} {'%':>5}  {'type':>4} {'pos':>4}  {'(x,y)':>9}  endpoints")
    for ((typ, pos), f) in freq.most_common(args.top):
        x, y = pos % W, pos // W
        if typ == 'h':
            endpoints = f"({x},{y}) -- ({x+1},{y})"
        else:
            endpoints = f"({x},{y}) -- ({x},{y+1})"
        pct = 100.0 * f / boards_analyzed
        print(f"{f:>4} {pct:>4.0f}%  {typ:>4} {pos:>4}  ({x:>2},{y:>2})  {endpoints}")

    threshold = int(args.threshold_frac * boards_analyzed)
    universal = sorted(
        ((typ, pos, f) for ((typ, pos), f) in freq.items() if f >= threshold),
        key=lambda r: -r[2],
    )
    print(f"\nMismatches appearing in >= {threshold}/{boards_analyzed} boards "
          f"({args.threshold_frac*100:.0f}% threshold): {len(universal)}")
    for (typ, pos, f) in universal:
        x, y = pos % W, pos // W
        print(f"  {typ} pos={pos} (x={x},y={y}) freq={f}/{boards_analyzed} "
              f"({100.0*f/boards_analyzed:.0f}%)")


if __name__ == "__main__":
    main()
