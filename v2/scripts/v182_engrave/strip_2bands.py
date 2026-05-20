#!/usr/bin/env python3
"""V182 ENGRAVE — strip 2 disjoint row-bands simultaneously.

If single-row strips are CSP-rigid (recover original or error), maybe
2-row strips with proper spacing find slack.
"""
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
    ap.add_argument('--row-a', type=int, required=True)
    ap.add_argument('--row-b', type=int, required=True)
    args = ap.parse_args()

    score, pl = load_board(args.input)
    new_pl = list(pl)
    for r in (args.row_a, args.row_b):
        for x in range(16):
            new_pl[r * 16 + x] = None
    write_partial(args.out, new_pl)
    print(f"stripped rows {args.row_a}, {args.row_b}")


if __name__ == '__main__':
    main()
