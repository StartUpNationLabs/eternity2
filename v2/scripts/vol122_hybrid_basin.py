#!/usr/bin/env python3
"""Vol-122 K9 — HYBRID BASIN: take interior from one record + border from another.

NEW INVENTION (user directive: INNOVATE OUTSIDE KNOWN HIGH SCORES):
Stop incrementally improving 452. Instead, explicitly construct a
HYBRID board that NO existing basin contains:

- Border (60 cells): take from vol-60 459 record
- Interior (196 cells): take from McGavin 469 record

If both basins share their 196 interior pieces with their own
border arrangements, then a hybrid would have all 256 cells
placed but may have:
1. Piece-uniqueness violations (interior pieces also used in vol-60's border? No, borders use only border pieces)
2. Color mismatches at the border/interior boundary
3. Internal interior arrangement that may not match border

Score the result. If it's PARTIAL (some mismatches), use it as ALNS seed.

This produces a partial that's structurally INSIDE NEITHER basin,
hence outside the rigid basin families.
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
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} BORDER_SOURCE.json INTERIOR_SOURCE.json OUT.json")
        sys.exit(1)
    border_src = Path(sys.argv[1])
    interior_src = Path(sys.argv[2])
    out_path = Path(sys.argv[3])

    pieces = load_pieces()
    side = 16

    with open(border_src) as f:
        bs = json.load(f)
    with open(interior_src) as f:
        is_ = json.load(f)
    border_placed = {e['pos']: (e['piece_id'], e['rotation']) for e in bs.get('placement', []) if e is not None}
    interior_placed = {e['pos']: (e['piece_id'], e['rotation']) for e in is_.get('placement', []) if e is not None}

    border_pos = []
    interior_pos = []
    for r in range(side):
        for c in range(side):
            pos = r * side + c
            if r in (0, side-1) or c in (0, side-1):
                border_pos.append(pos)
            else:
                interior_pos.append(pos)

    hybrid = {}
    for pos in border_pos:
        if pos in border_placed:
            hybrid[pos] = border_placed[pos]
    for pos in interior_pos:
        if pos in interior_placed:
            hybrid[pos] = interior_placed[pos]

    # Check piece-uniqueness
    used_pids = [hybrid[pos][0] for pos in hybrid]
    n_unique = len(set(used_pids))
    n_total = len(used_pids)
    print(f"hybrid placed: {n_total} (unique pieces: {n_unique})")
    if n_unique < n_total:
        print(f"  ⚠ {n_total - n_unique} duplicate pieces (would be illegal)")
        # Show duplicates
        from collections import Counter
        dups = [pid for pid, cnt in Counter(used_pids).items() if cnt > 1]
        print(f"  duplicate piece-ids: {dups[:10]}{'...' if len(dups) > 10 else ''}")

    # Score
    def score_board(board):
        total = 0
        for r in range(side):
            for c in range(side):
                pos = r * side + c
                if pos not in board: continue
                pid, rot = board[pos]
                edges = rotate(pieces[pid], rot)
                if c < side - 1 and (npos := pos + 1) in board:
                    npid, nrot = board[npos]
                    nedges = rotate(pieces[npid], nrot)
                    if edges[1] == nedges[3] and edges[1] != 0:
                        total += 1
                if r < side - 1 and (npos := pos + side) in board:
                    npid, nrot = board[npos]
                    nedges = rotate(pieces[npid], nrot)
                    if edges[2] == nedges[0] and edges[2] != 0:
                        total += 1
        return total

    s = score_board(hybrid)
    print(f"hybrid score: {s}")

    # Save (even if has duplicates, as a "starting partial" for repair)
    out_placement = []
    for pos in sorted(hybrid.keys()):
        pid, rot = hybrid[pos]
        out_placement.append({"pos": pos, "piece_id": pid, "rotation": rot})
    out = {
        "source": f"vol122_hybrid border={border_src.name} interior={interior_src.name}",
        "n_placed": n_total,
        "n_unique_pieces": n_unique,
        "score_matched": s,
        "placement": out_placement,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
