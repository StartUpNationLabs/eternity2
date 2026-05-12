#!/usr/bin/env python3
"""Vol-13 D5 — validate the rare-color stripe-extension rule on the corpus.

The Selby-Riordan generator rule (vol-7 memory): rare colors {1..5} only
appear on OPPOSITE edges of any piece. Direct consequence: rare colors
form straight stripes across the board, never bending at a single cell.

This script measures: in each community board, what fraction of "stripes
starting from a border rare-color" actually run straight to the opposite
border?

For each canonical-E2 board:
  * For each top-row cell c whose N edge carries a rare color r:
    - walk south through column c, checking that the S edge of each cell
      equals the previous N edge's color (which is automatic) AND that
      the S edge is a rare color (in {1..5}).
    - if the stripe makes it to the bottom border carrying a rare color
      all the way, it's "intact".
    - if it breaks at row k (where the piece is rare on top but not on
      bottom, or vice versa — Selby-Riordan says this CAN'T happen
      because rare pieces always have rare-rare on opposite edges) we
      record where.

Same for east/west horizontal stripes.

Output:
  * total #stripes, #intact, #broken, breakpoint distribution
  * if intact_rate > 0.95: rule is exact, propagator is sound
  * if 0.7 < intact_rate < 0.95: rule has known exceptions (e.g.
    corner pieces from vol-7) — propagator needs an exception list
  * if intact_rate < 0.7: rule is approximate; weaker propagator
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path


W = H = 16
BORDER = 0
RARE = {1, 2, 3, 4, 5}


def load_board(path: Path):
    with open(path) as f:
        b = json.load(f)
    url = b.get('url', '')
    # Extract board_edges= blob
    import re
    m = re.search(r'board_edges=([a-z]+)', url)
    if not m:
        return None
    blob = m.group(1)
    if len(blob) < W * H * 4:
        return None
    quads = []
    for pos in range(W * H):
        c = blob[pos*4:pos*4+4]
        if len(c) < 4:
            return None
        quads.append(tuple(ord(ch) - ord('a') for ch in c))
    return {
        'quads': quads,
        'puzzle': b.get('puzzle'),
        'interior_matched': b.get('interior_matched'),
        'pieces_placed': b.get('pieces_placed'),
        'path': str(path.name),
    }


def analyze_vertical_stripes(quads):
    """For each column c (1..14 excluding actual corners — but stripe
    starts from row 0's N edge which is the BORDER side; rare colors
    appear on row 0's S edge facing the interior).

    Actually: row 0 is the top border row. Its N edge is BORDER (color 0).
    Its S edge faces row 1's N edge — that's the first internal edge.
    The vertical stripe at column c is defined as: the colors on edges
    between rows r and r+1 in column c, for r = 0..14.

    Stripe[c][r] = quads[r*W + c][2]  (S edge of row r) = quads[(r+1)*W+c][0]  (N of row r+1).

    A "rare stripe" means stripe[c][r] is in RARE for all r where the cell
    is interior (r=0..14, but the cell at row 15 has its S edge = BORDER).

    We measure: starting from each column c, does the stripe alternate
    rare/non-rare or stay rare? The Selby-Riordan rule says any piece with
    a rare color on one edge has the OPPOSITE edge as ALSO rare (if it has
    a 2nd rare edge) OR has only that one rare edge. So a stripe of all-rare
    is possible, but a stripe with mixed rare+non-rare is also possible
    (the piece had 1 rare + 3 non-rare).

    Let me reformulate. The rule is about *piece* structure:
    if a piece has 2 rare edges, they are opposite.

    Implication for stripes: if cell (r, c) has rare on its N edge AND a
    rare on its S edge, the piece has 2 rare edges and they're on
    opposite-direction sides (which N and S are). Good. But if a piece
    has 1 rare on N and a NON-rare on S, that's compatible with the
    rule (only one rare edge).

    So the rule does NOT force stripes. It only forces that within a
    single piece, two rare edges are not on adjacent sides. A stripe of
    rare-edges propagating straight requires every cell along it to be
    a 2-rare-edge piece.

    Let me check empirically how often rare colors ACTUALLY form
    stripes. Maybe the rule combined with the piece-set distribution
    naturally produces stripes most of the time.
    """
    n_segments = 0  # total adjacent vertical edge pairs
    n_pair_both_rare = 0
    n_pair_one_rare_one_not = 0
    n_pair_neither = 0

    for c in range(W):
        for r in range(H - 1):
            # Edge between row r and row r+1 at column c = S of (r,c) = N of (r+1,c)
            s_edge = quads[r * W + c][2]
            n_edge = quads[(r+1) * W + c][0]
            # These should match (matched board). Skip if mismatched.
            if s_edge != n_edge:
                continue
            # Look at the edges of the cell (r+1, c): N is rare?, and S of same cell?
            cell_n = quads[(r+1) * W + c][0]
            cell_s = quads[(r+1) * W + c][2]
            # Skip if either is BORDER (cell at row H-1 has S=BORDER)
            if cell_n == BORDER or cell_s == BORDER:
                continue
            n_is_rare = cell_n in RARE
            s_is_rare = cell_s in RARE
            n_segments += 1
            if n_is_rare and s_is_rare:
                n_pair_both_rare += 1
            elif n_is_rare or s_is_rare:
                n_pair_one_rare_one_not += 1
            else:
                n_pair_neither += 1

    return n_segments, n_pair_both_rare, n_pair_one_rare_one_not, n_pair_neither


def analyze_horizontal_stripes(quads):
    n_segments = 0
    n_pair_both_rare = 0
    n_pair_one_rare_one_not = 0
    n_pair_neither = 0

    for r in range(H):
        for c in range(W):
            cell_w = quads[r * W + c][3]
            cell_e = quads[r * W + c][1]
            if cell_w == BORDER or cell_e == BORDER:
                continue
            w_is_rare = cell_w in RARE
            e_is_rare = cell_e in RARE
            n_segments += 1
            if w_is_rare and e_is_rare:
                n_pair_both_rare += 1
            elif w_is_rare or e_is_rare:
                n_pair_one_rare_one_not += 1
            else:
                n_pair_neither += 1

    return n_segments, n_pair_both_rare, n_pair_one_rare_one_not, n_pair_neither


def main():
    corpus = Path('output/community_corpus')
    # Filter to canonical-E2 only
    index_path = corpus / '_index.tsv'
    canonical = []
    with open(index_path) as f:
        next(f)  # header
        for line in f:
            cols = line.rstrip('\n').split('\t')
            score, placed, puzzle = cols[0], cols[1], cols[2]
            json_name = cols[-1]
            if puzzle in ('Eternity2', 'EternityII', 'E2nc'):
                canonical.append((int(score), corpus / json_name))
    canonical.sort(reverse=True)
    print(f"Canonical-E2 boards: {len(canonical)}")

    # Aggregate stats across boards weighted by quality (score >= 440)
    boards = []
    for score, path in canonical:
        b = load_board(path)
        if b is None:
            continue
        boards.append((score, b))

    print(f"successfully loaded: {len(boards)}")
    print()

    # Per board: pair statistics
    print(f"{'score':>5} {'placed':>6}  Vsegs   Vrr  Vrn  Vnn    %rr   |   Hsegs   Hrr  Hrn  Hnn    %rr")
    rr_aggregate_v = 0
    seg_aggregate_v = 0
    rr_aggregate_h = 0
    seg_aggregate_h = 0
    rare_only_pieces_consistent = True
    for score, b in boards[:20]:
        q = b['quads']
        ns_v, both_v, one_v, none_v = analyze_vertical_stripes(q)
        ns_h, both_h, one_h, none_h = analyze_horizontal_stripes(q)
        pct_rr_v = both_v / (both_v + one_v) if (both_v + one_v) > 0 else 0
        pct_rr_h = both_h / (both_h + one_h) if (both_h + one_h) > 0 else 0
        # Aggregate
        rr_aggregate_v += both_v
        seg_aggregate_v += both_v + one_v
        rr_aggregate_h += both_h
        seg_aggregate_h += both_h + one_h
        print(f"{score:>5} {b['pieces_placed']:>6}  {ns_v:>5} {both_v:>5} {one_v:>4} {none_v:>4}  {100*pct_rr_v:5.1f}%  |  {ns_h:>5} {both_h:>5} {one_h:>4} {none_h:>4}  {100*pct_rr_h:5.1f}%")

    print()
    if seg_aggregate_v > 0:
        pct_v = rr_aggregate_v / seg_aggregate_v
        print(f"VERTICAL aggregate (top-20 boards, conditional on at least 1 rare): {rr_aggregate_v}/{seg_aggregate_v} = {100*pct_v:.1f}% of cells with rare-on-{{N or S}} also have rare on the OTHER end")
    if seg_aggregate_h > 0:
        pct_h = rr_aggregate_h / seg_aggregate_h
        print(f"HORIZONTAL aggregate (top-20 boards): {rr_aggregate_h}/{seg_aggregate_h} = {100*pct_h:.1f}% of cells with rare-on-{{W or E}} also have rare on the OTHER end")


if __name__ == '__main__':
    main()
