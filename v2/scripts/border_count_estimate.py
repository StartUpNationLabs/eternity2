#!/usr/bin/env python3
"""Estimate the number of feasible E2 borders via two methods:

1. **Transfer-matrix lower bound (no piece-uniqueness)**: count walks
   around the perimeter where adjacent perimeter colors match.
   Treats pieces as REUSABLE — gives an upper bound on the true count.

2. **Random sampling estimate**: do K randomized backtracks with
   different seeds; count distinct borders found per second to
   extrapolate (fast Python proof-of-life).

Goal: tell us whether the feasible border count is 10², 10⁸, or 10²⁰
so we know whether to ENUMERATE all (small) or SAMPLE diversely (large).
"""

import argparse
import collections
import time
import sys


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


def rotate(q, r):
    return q[(4 - r) % 4:] + q[:(4 - r) % 4]


def classify(q):
    """Return 'corner','edge','inner' and the rotation+(prev,next,inward) options
    when placed on TOP-row (so we can compute color profiles)."""
    n_border = sum(1 for c in q if c == 0)
    if n_border == 2:
        # Adjacent? E2 has no diagonal corners.
        adj = [(0,1),(1,2),(2,3),(3,0)]
        if any(q[i]==0 and q[j]==0 for i,j in adj):
            return 'corner'
    if n_border == 1:
        return 'edge'
    return 'inner'


def edge_outward_pair(q):
    """For an edge piece, return (perim_left_color, perim_right_color)
    when oriented with BORDER facing outward (top-row orientation).
    The pair represents (color toward previous perim cell, color toward next).
    Result is direction-agnostic: returns sorted-pair? No — direction matters
    for adjacency. We return both orientations: when placed in walk direction
    or reversed. So returns frozenset of two ordered (L,R) tuples."""
    out = set()
    for r in range(4):
        rq = rotate(q, r)
        t, ri, b, le = rq
        if t == 0:
            # On top-row in default orientation.
            # 'left along walk' = le, 'right along walk' = ri.
            out.add((le, ri))
    return out


def transfer_count(pieces):
    """Approximate count: treat the 60-cell border as a cycle in a
    color-graph. Per-cell vertex = 'inward-edge color', and adjacency
    requires that consecutive cells have a perimeter-color in common.

    Build a transition matrix T[c_from -> c_to] = number of edge pieces
    that can connect color c_from on their LEFT face and c_to on their
    RIGHT face. Cycle-count = trace(T^60) ... but we have 4 corners
    interrupting, so handle separately.

    For simplicity, we fold corners in by computing the count for
    each of 4 segments (top, right, bottom, left), each of length 14
    edge-pieces, with fixed boundary colors at the corners.

    This OVERCOUNTS because pieces are reused across cells (we have
    only 56 unique edges and 4 corners). The transfer-matrix count
    treats every cell as drawing from the FULL bag with replacement.
    But it gives an upper bound and shape.
    """
    edges = [q for q in pieces if classify(q) == 'edge']
    corners = [q for q in pieces if classify(q) == 'corner']
    n_colors = max(max(c for c in q) for q in pieces) + 1

    # Build T: for an edge piece on TOP row (t=0), it presents (le, ri).
    # T[le][ri] = how many distinct edge-pieces can serve.
    T = [[0]*n_colors for _ in range(n_colors)]
    for q in edges:
        for r in range(4):
            rq = rotate(q, r)
            t, ri, b, le = rq
            if t == 0:
                T[le][ri] += 1
    # Corner: presents (le_along_top, b_into_left_col) = (color_to_previous_in_walk_along_top, color_to_next_in_walk_into_left_col).
    # For TL corner (t==0 AND le==0):
    # along walk we leave TL toward (1,0): 'next' in walk = ri (top row).
    # we arrive at TL from (0,1): the previous-walk color = b (left col).
    # So a TL placement gives boundary colors (incoming = b, outgoing = ri).
    # We enumerate (incoming, outgoing) pairs per corner kind.

    def corner_pairs(kind, qlist):
        pairs = collections.Counter()
        for q in qlist:
            for r in range(4):
                rq = rotate(q, r)
                t, ri, b, le = rq
                if kind == 'TL' and t == 0 and le == 0:
                    pairs[(b, ri)] += 1   # from-left-col, to-top-row
                elif kind == 'TR' and t == 0 and ri == 0:
                    pairs[(le, b)] += 1   # from-top-row, to-right-col
                elif kind == 'BR' and b == 0 and ri == 0:
                    pairs[(t, le)] += 1   # from-right-col, to-bottom-row
                elif kind == 'BL' and b == 0 and le == 0:
                    pairs[(ri, t)] += 1   # from-bottom-row, to-left-col
        return pairs

    tl = corner_pairs('TL', corners)
    tr = corner_pairs('TR', corners)
    br = corner_pairs('BR', corners)
    bl = corner_pairs('BL', corners)
    print(f'corner placement counts: TL={sum(tl.values())} TR={sum(tr.values())} BR={sum(br.values())} BL={sum(bl.values())}', file=sys.stderr)

    # For each segment (between two adjacent corners), with fixed
    # incoming color c_in and outgoing color c_out: count walks of
    # length 14 (14 edge pieces) in T from c_in to c_out.
    # Use T^14[c_in][c_out].
    import numpy as np
    M = np.array(T, dtype=np.float64)
    print(f'T shape: {M.shape}', file=sys.stderr)
    M14 = np.linalg.matrix_power(M, 14)

    # Total count = sum over (TL, TR, BR, BL) corner choices of
    #   tl[(c_w_left, c_a)] *           # TL: incoming from left-col, outgoing to top-row
    #   M14[c_a][c_b] *                 # top-row: 14 edges from c_a to c_b
    #   tr[(c_b, c_c)] *                # TR: incoming from top, outgoing to right
    #   M14[c_c][c_d] *                 # right-col: 14 edges from c_c to c_d
    #   br[(c_d, c_e)] *                # BR: in from right, out to bottom
    #   M14[c_e][c_f] *                 # bottom-row: 14 edges from c_e to c_f
    #   bl[(c_f, c_g)] *                # BL: in from bottom, out to left
    #   M14[c_g][c_w_left]              # left-col: 14 edges from c_g back to c_w_left (cycle closure)
    #
    # 8-deep loop with up-front filtering = sum over corner placements,
    # multiplied by matrix entries. Still expensive but tractable
    # because there are few corner placements.

    total = 0.0
    n_terms = 0
    for (cwl, ca), tl_n in tl.items():
        for (cb, cc), tr_n in tr.items():
            for (cd, ce), br_n in br.items():
                for (cf, cg), bl_n in bl.items():
                    contrib = (tl_n * M14[ca][cb] * tr_n * M14[cc][cd]
                               * br_n * M14[ce][cf] * bl_n * M14[cg][cwl])
                    if contrib > 0:
                        total += contrib
                        n_terms += 1
    return total, n_terms, M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--puzzle', default='../data/puzzles/size_16_official_eternity.csv')
    args = ap.parse_args()

    size, pieces = load_pieces(args.puzzle)
    n_corner = sum(1 for q in pieces if classify(q) == 'corner')
    n_edge = sum(1 for q in pieces if classify(q) == 'edge')
    n_inner = sum(1 for q in pieces if classify(q) == 'inner')
    print(f'pieces: {len(pieces)} (corners={n_corner}, edges={n_edge}, inner={n_inner})')

    print(f'\nNAIVE upper bound (no constraints):')
    import math
    naive = math.factorial(n_corner) * math.factorial(n_edge) * (4 ** n_corner)  # corners can rotate but only 1 valid rot each
    # Actually per-corner only 1 valid rotation places it correctly (the BORDER edges must face out).
    # And per-edge piece, only 1 valid rotation places BORDER outward when on its side.
    # So real upper bound is just 4! × 56! = arrangements with no color check.
    upper = math.factorial(4) * math.factorial(56)
    print(f'  4! × 56! = {upper:.3e}')

    print(f'\nTRANSFER-MATRIX (color match only, pieces with replacement):')
    t0 = time.time()
    total, n_terms, M = transfer_count(pieces)
    print(f'  ≈ {total:.3e} ({n_terms} non-zero corner-quadruple terms)')
    print(f'  computed in {time.time()-t0:.1f}s')
    print(f'  CAVEAT: this is HUGE because pieces are not deduplicated;')
    print(f'  the true count is much smaller (each piece used at most once).')

    # Quick sanity: T row sums (number of edge placements per left-color).
    print(f'\n  Per-color T row sums (incoming-color → number of edge placements):')
    for c in range(M.shape[0]):
        s = M[c].sum()
        if s > 0:
            print(f'    color {c}: {int(s)} placements')


if __name__ == '__main__':
    main()
