#!/usr/bin/env python3
"""V182 ENGRAVE — strip an arbitrary horizontal band (rows R..R+H)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


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
    ap.add_argument('--row-start', type=int, required=True)
    ap.add_argument('--row-end', type=int, required=True, help='exclusive')
    args = ap.parse_args()

    score, pl = load_board(args.input)
    print(f"input score={score}, stripping rows {args.row_start}..{args.row_end - 1}")
    new_pl = list(pl)
    for y in range(args.row_start, args.row_end):
        for x in range(16):
            new_pl[y * 16 + x] = None
    write_partial(args.out, new_pl)
    n_left = sum(1 for p in new_pl if p is not None)
    print(f"  {n_left}/256 cells remain placed")


if __name__ == '__main__':
    main()
