#!/usr/bin/env python3
"""Analyze mismatch geometry of an ALNS board JSON output.

Usage:
  python3 scripts/analyze_mismatch_geometry.py <path-to-board.json> [--puzzle PATH]

The JSON must have a 'placement' field: list of {pos, piece_id, rotation}
(piece_id 0-indexed matching the puzzle CSV's line order).

Output: per-row mismatch counts + connected-component sizes + bucas URL.
"""
import argparse
import json
import sys
from collections import deque
from pathlib import Path

W = H = 16

def load_pieces(puzzle_path):
    pieces = []
    with open(puzzle_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    for l in lines[1:]:
        cols = l.split(',')
        def cv(s):
            v = int(s, 2)
            return 0 if v == 65535 else v
        t = cv(cols[0]); r = cv(cols[1]); b = cv(cols[2]); ll = cv(cols[3])
        pieces.append([t, r, b, ll])
    return pieces

def rot_edges(e, rot):
    if rot == 0: return e
    if rot == 1: return [e[3], e[0], e[1], e[2]]
    if rot == 2: return [e[2], e[3], e[0], e[1]]
    if rot == 3: return [e[1], e[2], e[3], e[0]]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board_json')
    ap.add_argument('--puzzle', default='/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/puzzles/size_16_official_eternity.csv')
    args = ap.parse_args()
    data = json.load(open(args.board_json))
    pieces = load_pieces(args.puzzle)
    cell = [None] * (W * H)
    for p in data.get('placement', []):
        if p is not None:
            cell[p['pos']] = (p['piece_id'], p['rotation'])
    matched = total = 0
    mismatches = []
    mismatches_per_cell = [0] * (W * H)
    for y in range(H):
        for x in range(W):
            pos = y*W + x
            if cell[pos] is None: continue
            pid, rot = cell[pos]
            if pid >= len(pieces): continue
            e = rot_edges(pieces[pid], rot)
            if x+1 < W and cell[pos+1] is not None:
                pid_n, rot_n = cell[pos+1]
                en = rot_edges(pieces[pid_n], rot_n)
                total += 1
                if e[1] == en[3]:
                    matched += 1
                else:
                    mismatches.append((pos, pos+1))
                    mismatches_per_cell[pos] += 1
                    mismatches_per_cell[pos+1] += 1
            if y+1 < H and cell[pos+W] is not None:
                pid_n, rot_n = cell[pos+W]
                en = rot_edges(pieces[pid_n], rot_n)
                total += 1
                if e[2] == en[0]:
                    matched += 1
                else:
                    mismatches.append((pos, pos+W))
                    mismatches_per_cell[pos] += 1
                    mismatches_per_cell[pos+W] += 1
    print(f"Total interior edges: {total}, matched: {matched}/{total} ({100*matched/total:.1f}%)")
    print(f"Mismatches: {total - matched}")
    # Per-row mismatch endpoints
    per_row = [0] * H
    for a, b in mismatches:
        ya = a // W
        yb = b // W
        per_row[ya] += 1
        if yb != ya:
            per_row[yb] += 1
    print("\nPer-row mismatch endpoints:")
    for y in range(H):
        bar = "█" * per_row[y]
        print(f"  row {y:2}: {per_row[y]:3}  {bar}")
    # Component analysis
    mismatch_cells = set()
    for a, b in mismatches:
        mismatch_cells.add(a); mismatch_cells.add(b)
    seen = set()
    components = []
    for start in mismatch_cells:
        if start in seen: continue
        comp = [start]
        queue = deque([start])
        seen.add(start)
        while queue:
            p = queue.popleft()
            x, y = p % W, p // W
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    n = ny * W + nx
                    if n in mismatch_cells and n not in seen:
                        seen.add(n); queue.append(n); comp.append(n)
        components.append(comp)
    components.sort(key=len, reverse=True)
    print(f"\nMismatch cells: {len(mismatch_cells)}")
    print(f"Connected components: {len(components)}")
    for i, c in enumerate(components[:5]):
        rows = sorted(set(p // W for p in c))
        print(f"  comp #{i}: size={len(c)}  rows={min(rows)}-{max(rows)}")
    if 'bucas_url' in data:
        print(f"\nbucas: {data['bucas_url']}")

if __name__ == '__main__':
    main()
