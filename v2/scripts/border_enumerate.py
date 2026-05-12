#!/usr/bin/env python3
"""Enumerate / sample feasible E2 border arrangements.

The border (60 cells: 4 corners + 56 edges) has NO hint constraints —
all 5 official hints are interior. So a feasible border is just a
permutation of {4 corners, 56 edges} around the perimeter such that
adjacent perimeter colors match.

Perimeter walk order (clockwise from TL):
  TL=(0,0) → top row R: (1..14,0) → TR=(15,0)
         → right col D: (15,1..14) → BR=(15,15)
         → bottom row L: (14..1,15) → BL=(0,15)
         → left col U: (0,14..1) → TL

For an edge piece on a side, we report (left_in, right_in) along the
perimeter walk direction, plus inward color and rotation.

Output: JSON list of borders. Each entry =
  { "border": [{piece_id, rotation, x, y}, ...60 cells in walk order],
    "inward":  [color per cell, length 60],
    "signature": <stable tuple>
  }
"""

import argparse
import itertools
import json
import os
import random
import sys
import time
from collections import defaultdict


def parse_word(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4: continue
            quad = tuple(parse_word(cols[i]) for i in range(4))
            pieces.append((pid, quad))
    return size, pieces


def rotate(q, r):
    return q[(4 - r) % 4:] + q[:(4 - r) % 4]


# Walk a 16x16 border clockwise from TL. Returns 60 (x,y) pairs.
def perimeter_cells(size=16):
    cells = []
    # Top row L→R
    for x in range(size):
        cells.append((x, 0))
    # Right col T→B (skip TR)
    for y in range(1, size):
        cells.append((size - 1, y))
    # Bottom row R→L (skip BR)
    for x in range(size - 2, -1, -1):
        cells.append((x, size - 1))
    # Left col B→T (skip BL and TL)
    for y in range(size - 2, 0, -1):
        cells.append((0, y))
    return cells


def cell_kind(x, y, size=16):
    """'TL','TR','BR','BL' or 'top','right','bottom','left'."""
    if (x, y) == (0, 0): return 'TL'
    if (x, y) == (size - 1, 0): return 'TR'
    if (x, y) == (size - 1, size - 1): return 'BR'
    if (x, y) == (0, size - 1): return 'BL'
    if y == 0: return 'top'
    if x == size - 1: return 'right'
    if y == size - 1: return 'bottom'
    if x == 0: return 'left'
    return 'interior'


def placements_for(quad, kind):
    """Return list of (rotation, prev_color, next_color, inward_color)
    for placing this piece at a perimeter cell of given 'kind'.
    prev_color = the color facing the previous perimeter cell (in walk dir).
    next_color = the color facing the next perimeter cell.
    """
    out = []
    for r in range(4):
        rq = rotate(quad, r)  # (top, right, bottom, left)
        t, ri, b, le = rq
        if kind == 'TL':
            # need top=0 AND left=0; prev=N/A; next=ri (along top row); inward=irrelevant for corner adjacency calc, but inward = (b, ri) two-edge
            if t == 0 and le == 0:
                # walk: TL → next is (1,0); next color = ri
                # prev is the wrap-around from left col (also implicit corner)
                # We separate corner adjacency: corner has NO prev (cycle) but has 2 outgoing matches: ri (top dir) and b (left col dir).
                out.append((r, None, ri, b, le, t))  # see usage below
        elif kind == 'TR':
            if t == 0 and ri == 0:
                # prev color (along top row, facing left) = le
                # next color (along right col, facing down)  = b
                out.append((r, le, b, ri, t, None))
        elif kind == 'BR':
            if ri == 0 and b == 0:
                # prev (along right col coming down, facing up) = t
                # next (along bottom row going left, facing left) = le
                out.append((r, t, le, b, ri, None))
        elif kind == 'BL':
            if b == 0 and le == 0:
                # prev (along bottom row, facing right) = ri
                # next (along left col going up, facing up) = t
                out.append((r, ri, t, le, b, None))
        elif kind == 'top':
            # prev = left side facing previous (=le); next = right side facing next (=ri)
            # border edge must be top → t == 0
            if t == 0:
                out.append((r, le, ri, b, None, None))
        elif kind == 'right':
            # walk down, border on right → ri == 0
            # prev (above) faces up = t; next (below) faces down = b
            if ri == 0:
                out.append((r, t, b, le, None, None))
        elif kind == 'bottom':
            # walk leftward, border on bottom → b == 0
            # prev (to the right) faces right = ri; next (to the left) faces left = le
            if b == 0:
                out.append((r, ri, le, t, None, None))
        elif kind == 'left':
            # walk upward, border on left → le == 0
            # prev (below) faces down = b; next (above) faces up = t
            if le == 0:
                out.append((r, b, t, ri, None, None))
    return out


def build_placements(pieces, cells):
    """For each perimeter cell index 0..59, list of (piece_id, rotation, prev, next, inward) tuples.
    For corners we also record alt_inward; the corner has 2 matching directions, modeled as prev/next."""
    n = len(cells)
    table = [[] for _ in range(n)]
    for idx, (x, y) in enumerate(cells):
        kind = cell_kind(x, y)
        for pid, quad in pieces:
            for plac in placements_for(quad, kind):
                r, prev, nxt, inward, alt_in1, alt_in2 = plac
                table[idx].append({
                    'pid': pid, 'rot': r, 'prev': prev, 'next': nxt,
                    'inward': inward, 'alt1': alt_in1, 'alt2': alt_in2,
                    'kind': kind,
                })
    return table


def solve_borders(table, n_target, time_budget_s, seed=0xCAFEBABE, randomize=True):
    """Backtrack search over perimeter cells 0..59. Yields up to n_target distinct borders.

    Constraint: at each step, current piece's `prev` color must equal previous cell's `next` color
    (or, on the first cell, any). Last cell (LL going back to TL on the cycle) must close the loop.

    The cycle constraint requires the LAST cell's `next` color == FIRST cell's `prev` color.
    To handle this, we pick the TL corner's outgoing 'next' color first, then enforce the loop on cell 59.
    """
    rng = random.Random(seed)
    n = len(table)

    used_pids = set()
    chosen = [None] * n
    found = []
    deadline = time.time() + time_budget_s
    nodes = [0]

    # Precompute index by 'prev' color for each cell, sorted.
    by_prev = []
    for cell_idx in range(n):
        d = defaultdict(list)
        for opt in table[cell_idx]:
            key = opt['prev']  # may be None for TL corner
            d[key].append(opt)
        by_prev.append(d)

    def candidates(cell_idx, required_prev):
        if cell_idx == 0:
            # TL corner, no prev constraint
            opts = list(itertools.chain.from_iterable(by_prev[0].values()))
        else:
            opts = by_prev[cell_idx].get(required_prev, [])
        if randomize:
            rng.shuffle(opts)
        return opts

    def recurse(cell_idx, required_prev, first_prev_needed):
        nodes[0] += 1
        if time.time() > deadline:
            return
        if len(found) >= n_target:
            return
        if cell_idx == n:
            # Closure: last cell's `next` must match first_prev_needed (TL's `prev` direction).
            # For TL corner: 'prev' is None in our model — but the corner DOES have an
            # incoming color from the left column, which we model as alt_in1 of TL.
            # See 'TL' branch in placements_for: alt_in1 = le, alt_in2 = t (we used these slots).
            # Last cell next_color should equal TL's `le` (which we stored as alt1).
            tl = chosen[0]
            last = chosen[-1]
            if last['next'] == tl['alt1']:
                # Found a valid border!
                board_data = []
                for i in range(n):
                    c = chosen[i]
                    board_data.append({'pid': c['pid'], 'rot': c['rot'], 'inward': c['inward'],
                                       'alt1': c['alt1'], 'alt2': c['alt2'], 'kind': c['kind']})
                found.append(board_data)
            return

        for opt in candidates(cell_idx, required_prev):
            if opt['pid'] in used_pids:
                continue
            used_pids.add(opt['pid'])
            chosen[cell_idx] = opt
            recurse(cell_idx + 1, opt['next'], first_prev_needed)
            used_pids.remove(opt['pid'])
            chosen[cell_idx] = None
            if time.time() > deadline or len(found) >= n_target:
                return

    recurse(0, None, None)
    return found, nodes[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--puzzle', default='../data/puzzles/size_16_official_eternity.csv')
    ap.add_argument('--n-target', type=int, default=200)
    ap.add_argument('--time-budget', type=int, default=120, help='seconds')
    ap.add_argument('--seed', type=int, default=0xCAFEBABE)
    ap.add_argument('--out', default='output/borders/border_library.json')
    args = ap.parse_args()

    size, pieces = load_pieces(args.puzzle)
    print(f'puzzle: {size}x{size}, pieces: {len(pieces)}', file=sys.stderr)

    cells = perimeter_cells(size)
    table = build_placements(pieces, cells)
    print(f'perimeter cells: {len(cells)}; placements/cell sample = '
          f'{[len(t) for t in table[:8]]}...', file=sys.stderr)

    t0 = time.time()
    borders, nodes = solve_borders(table, args.n_target, args.time_budget,
                                   seed=args.seed, randomize=True)
    elapsed = time.time() - t0
    print(f'\nfound {len(borders)} borders in {elapsed:.1f}s, {nodes} nodes', file=sys.stderr)

    # Write output: just enough metadata to reconstruct
    out = {
        'puzzle': args.puzzle,
        'walk': cells,
        'borders': [
            [{'pid': c['pid'], 'rot': c['rot'], 'inward': c['inward']} for c in b]
            for b in borders
        ],
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(out, f)
    print(f'wrote {args.out} ({len(borders)} borders)', file=sys.stderr)


if __name__ == '__main__':
    main()
