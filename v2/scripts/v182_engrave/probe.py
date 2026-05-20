#!/usr/bin/env python3
"""V182 ENGRAVE — strip last K rows from a board and try CSP-fill for
the best completion.

The hypothesis: if a V175 build scores 449-454 with rows 12-15 being
weak (per the seed1-vs-seed13 finding earlier today), then stripping
rows 12-15 and running CSP-fill (which is exhaustive within budget)
might find a better bottom 4 rows.

Output: partial JSON (top 192 cells of a V175 build, bottom 64 cells null).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_board(path, size=16):
    d = json.loads(Path(path).read_text())
    pl = d.get('placement', [])
    placement = [None] * (size * size)
    has_pos = any(isinstance(e, dict) and 'pos' in e for e in pl if e is not None)
    for i, entry in enumerate(pl):
        if entry is None: continue
        pos = int(entry['pos']) if has_pos else i
        placement[pos] = (int(entry['piece_id']), int(entry['rotation']))
    return d.get('matched'), placement


def write_partial(path, placement, size=16):
    pl = []
    for pos, ent in enumerate(placement):
        if ent is None:
            pl.append(None)
        else:
            pid, rot = ent
            pl.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    Path(path).write_text(json.dumps({'placement': pl, 'matched': 0}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--strip-rows', type=int, default=4, help='Strip last K rows')
    args = ap.parse_args()

    score, pl = load_board(args.input)
    print(f"input: {args.input} score={score}")

    # Strip last K rows.
    stripped = list(pl)
    n_stripped = 0
    for y in range(16 - args.strip_rows, 16):
        for x in range(16):
            pos = y * 16 + x
            if stripped[pos] is not None:
                stripped[pos] = None
                n_stripped += 1
    print(f"stripped {n_stripped} cells in rows {16 - args.strip_rows}..15")

    write_partial(args.out, stripped)
    print(f"saved partial to {args.out}")


if __name__ == '__main__':
    main()
