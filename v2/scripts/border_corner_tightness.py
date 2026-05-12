#!/usr/bin/env python3
"""Stronger surrogate: per inner-corner cell (1,1), (14,1), (1,14), (14,14)
count the inner pieces that can satisfy BOTH boundary colors.

A border that leaves some inner corner cell with 0 candidate pieces is
provably infeasible. A border with very few candidates per inner corner
is tightly constrained — likely a hard interior. A border with many
candidates per inner corner has more flexibility — likely easier."""

import json
from collections import Counter

PUZZLE = '../data/puzzles/size_16_official_eternity.csv'
LIB = 'output/borders/sample_10k.jsonl'
CORPUS_453 = 'output/night-archive/HISTORIC_first_453_1778557672.json'


def parse_word(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for line in f:
            cols = line.strip().split(',')
            if len(cols) < 4: continue
            quad = tuple(parse_word(cols[i]) for i in range(4))
            pieces.append(quad)
    return size, pieces


def rotated(q, r):
    t, ri, b, le = q
    if r == 0: return (t, ri, b, le)
    if r == 1: return (le, t, ri, b)
    if r == 2: return (b, le, t, ri)
    if r == 3: return (ri, b, le, t)


def perimeter_cells(size):
    cells = []
    for x in range(size): cells.append((x, 0))
    for y in range(1, size): cells.append((size-1, y))
    for x in range(size-2, -1, -1): cells.append((x, size-1))
    for y in range(size-2, 0, -1): cells.append((0, y))
    return cells


def cell_kind(x, y, sz):
    mx = sz - 1
    if (x,y)==(0,0): return 'TL'
    if (x,y)==(mx,0): return 'TR'
    if (x,y)==(mx,mx): return 'BR'
    if (x,y)==(0,mx): return 'BL'
    if y == 0: return 'top'
    if x == mx: return 'right'
    if y == mx: return 'bottom'
    if x == 0: return 'left'
    return 'inner'


def inward_color(quad, rot, kind):
    e = rotated(quad, rot)
    t, ri, b, le = e
    if kind == 'top': return b
    if kind == 'right': return le
    if kind == 'bottom': return t
    if kind == 'left': return ri
    return None


def inner_corner_constraints(border, cells, pieces, size=16):
    """For each of the 4 inner-corner cells, return the pair of
    boundary colors (top, left), (top, right), (bottom, left), (bottom, right)
    facing the boundary.

    Inner-corner cells: (1,1), (14,1), (1,14), (14,14).
    Each touches 2 boundary cells. Get the inward colors of those.
    """
    pos_to_cell = {pos: i for i, pos in enumerate(cells)}
    inner_corners = [(1, 1), (14, 1), (1, 14), (14, 14)]
    out = []
    for (x, y) in inner_corners:
        # neighbors on the border
        neighbors = []
        # top: (x, 0) — only if y == 1
        if y == 1:
            i = pos_to_cell[(x, 0)]
            pid, rot = border[i]
            ic = inward_color(pieces[pid], rot, cell_kind(x, 0, size))
            neighbors.append(('top', ic))
        # bottom: (x, 15) — only if y == 14
        if y == 14:
            i = pos_to_cell[(x, 15)]
            pid, rot = border[i]
            ic = inward_color(pieces[pid], rot, cell_kind(x, 15, size))
            neighbors.append(('bot', ic))
        # left: (0, y) — only if x == 1
        if x == 1:
            i = pos_to_cell[(0, y)]
            pid, rot = border[i]
            ic = inward_color(pieces[pid], rot, cell_kind(0, y, size))
            neighbors.append(('lft', ic))
        # right: (15, y) — only if x == 14
        if x == 14:
            i = pos_to_cell[(15, y)]
            pid, rot = border[i]
            ic = inward_color(pieces[pid], rot, cell_kind(15, y, size))
            neighbors.append(('rgt', ic))
        out.append(((x, y), neighbors))
    return out


def count_inner_pieces_matching(pieces, constraints):
    """Given a constraint set [(side_label, color), ...] for an
    inner-corner cell, count the number of (inner_piece, rotation) pairs
    where the piece's edges matching the same sides have those colors.
    """
    # Map our side labels to which face of the piece must match.
    # When the constraint says (top, c), the inner-corner cell's TOP edge
    # = c, meaning the piece's TOP face = c.
    label_to_face = {'top': 0, 'rgt': 1, 'bot': 2, 'lft': 3}
    count = 0
    for pid, q in enumerate(pieces):
        if sum(1 for c in q if c == 0) != 0: continue  # only inner pieces
        for r in range(4):
            e = rotated(q, r)
            ok = True
            for (side, c) in constraints:
                f = label_to_face[side]
                if e[f] != c:
                    ok = False
                    break
            if ok:
                count += 1
    return count


def main():
    size, pieces = load_pieces(PUZZLE)
    cells = perimeter_cells(size)

    # Score corpus 453
    corpus = json.load(open(CORPUS_453))
    pl = corpus['placement']
    cb = []
    for (x, y) in cells:
        c = pl[y*size + x]
        cb.append((c['piece_id'], c['rotation']))
    cc = inner_corner_constraints(cb, cells, pieces, size)
    print(f'Corpus 453 inner-corner constraints:')
    cc_scores = []
    for (xy, neigh) in cc:
        n = count_inner_pieces_matching(pieces, neigh)
        cc_scores.append(n)
        print(f'  inner-corner {xy}: constraints={neigh}, matching inner-piece-rotations: {n}')
    cc_min = min(cc_scores)
    cc_total = sum(cc_scores)
    print(f'  min={cc_min}, sum={cc_total}')

    # Now score the 10k library
    print(f'\nScoring 10k library...')
    library = []
    with open(LIB) as f:
        for line in f:
            border = [tuple(c) for c in json.loads(line)['border']]
            constraints = inner_corner_constraints(border, cells, pieces, size)
            scores = [count_inner_pieces_matching(pieces, n) for (_, n) in constraints]
            library.append({
                'border': border,
                'corner_scores': scores,
                'min': min(scores),
                'sum': sum(scores),
                'has_zero': 0 in scores,
            })

    print(f'\n10k library inner-corner tightness:')
    zeros = sum(1 for r in library if r['has_zero'])
    print(f'  borders with ANY inner-corner having 0 candidates (provably infeasible interior): {zeros}/{len(library)}')

    from collections import Counter
    min_dist = Counter(r['min'] for r in library)
    print(f'  min-across-4-corners histogram:')
    for k in sorted(min_dist.keys())[:15]:
        print(f'    min={k}: {min_dist[k]} borders')
    sums = [r['sum'] for r in library]
    sums.sort()
    print(f'  sum-across-4-corners: min={sums[0]} median={sums[len(sums)//2]} max={sums[-1]}')
    print(f'  corpus 453 sum: {cc_total}, min: {cc_min}')

    # Pick top by combined score: (1) no zero, (2) max sum
    feasible = [r for r in library if not r['has_zero']]
    print(f'\nfeasible (no inner-corner with 0): {len(feasible)}/{len(library)} ({100*len(feasible)/len(library):.1f}%)')
    feasible.sort(key=lambda r: -r['sum'])
    print(f'top-5 by sum:')
    for r in feasible[:5]:
        print(f'  scores={r["corner_scores"]} sum={r["sum"]}')
    print(f'\nbottom-5 by sum (still feasible):')
    for r in feasible[-5:]:
        print(f'  scores={r["corner_scores"]} sum={r["sum"]}')

    # Write top-1000 by sum
    top = feasible[:1000]
    with open('output/borders/top_1000_by_corner_tightness.jsonl', 'w') as f:
        for r in top:
            f.write(json.dumps({
                'border': [list(c) for c in r['border']],
                'corner_scores': r['corner_scores'],
                'sum': r['sum'],
                'min': r['min'],
            }) + '\n')
    print(f'\nwrote top-1000 by corner-tightness sum to output/borders/top_1000_by_corner_tightness.jsonl')


if __name__ == '__main__':
    main()
