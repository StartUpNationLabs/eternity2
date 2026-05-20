#!/usr/bin/env python3
"""V172 CHIASMUS — generate cross-basin row-interleave hybrids.

Pick top-N input boards by score, one per distinct corner-perm.
Generate all (i, j) × 3 schemes hybrid partials.
"""
from __future__ import annotations
import argparse
import itertools
import json
from pathlib import Path
from collections import defaultdict


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


def make_hybrid(A, B, scheme, size=16):
    used = set()
    h = [None] * (size * size)
    for y in range(size):
        src = A if scheme[y] == 'A' else B
        for x in range(size):
            pos = y * size + x
            ent = src[pos]
            if ent is None: continue
            pid, rot = ent
            if pid in used: continue
            used.add(pid)
            h[pos] = (pid, rot)
    return h


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
    ap.add_argument('--inputs', required=True, nargs='+',
                    help='Input board JSONs (or glob patterns)')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--top-n', type=int, default=8,
                    help='Top-N distinct-cp boards to use as parents')
    ap.add_argument('--min-score', type=int, default=440)
    args = ap.parse_args()

    import glob
    boards = []
    for pattern in args.inputs:
        boards.extend(glob.glob(pattern))
    print(f"Loading {len(boards)} candidate boards...")

    by_cp = defaultdict(list)
    for bp in boards:
        try:
            m, pl = load_board(bp)
        except Exception:
            continue
        if m is None or m < args.min_score: continue
        if not all(pl[c] is not None for c in (0, 15, 240, 255)): continue
        cp = (pl[0][0], pl[15][0], pl[240][0], pl[255][0])
        by_cp[cp].append((m, bp, pl))

    print(f"Found {len(by_cp)} distinct corner-perms with score ≥ {args.min_score}")
    # Pick top board per cp
    chosen = []
    for cp, items in by_cp.items():
        items.sort(reverse=True)
        chosen.append((items[0][0], cp, items[0][1], items[0][2]))
    chosen.sort(reverse=True)
    chosen = chosen[:args.top_n]
    print(f"Top {len(chosen)} cps by score:")
    for m, cp, bp, _ in chosen:
        print(f"  {m}  cp={cp}  {Path(bp).name}")

    # Generate hybrids
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    schemes = {
        'rowAB':    ['A' if i % 2 == 0 else 'B' for i in range(16)],
        'top8A':    ['A' if i < 8 else 'B' for i in range(16)],
        'border4A': ['A' if (i < 4 or i >= 12) else 'B' for i in range(16)],
        'mid8A':    ['B' if (i < 4 or i >= 12) else 'A' for i in range(16)],
    }
    count = 0
    for (mi, cpi, _, A), (mj, cpj, _, B) in itertools.combinations(chosen, 2):
        if cpi == cpj: continue
        for sname, scheme in schemes.items():
            tag = f"cp{cpi[0]}{cpi[1]}{cpi[2]}{cpi[3]}_x_cp{cpj[0]}{cpj[1]}{cpj[2]}{cpj[3]}_{sname}"
            tag = tag[:60]  # cap path length
            h = make_hybrid(A, B, scheme)
            out_path = out_dir / f"{tag}.json"
            write_partial(out_path, h)
            count += 1
    print(f"Generated {count} hybrid partials in {out_dir}")


if __name__ == '__main__':
    main()
