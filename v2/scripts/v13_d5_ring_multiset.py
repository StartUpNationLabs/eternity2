#!/usr/bin/env python3
"""Vol-13 D5 — verify the rare-color border-ring multiset invariant.

THE CLAIM: in canonical E2, every rare color in {1..5} lives ONLY on the
60-piece border ring's internal matchings. Specifically:
  * 56 edge pieces × 2 rare edges = 112 slots on edge-to-edge ring matchings
  * 4 corner pieces × 2 rare edges = 8 slots on corner-edge matchings
  * Total 120 slots = 60 internal ring matchings × 2 endpoints.

Each rare color appears 24 times total. As 60 ring matchings consume 120
endpoints, and each color matches in pairs, each rare color must appear
24/2 = 12 times as a matched border-ring pair in any full solution.

THE TEST: in each community-corpus board, walk the border ring
(perimeter cells: row 0, col 15, row 15, col 0 going clockwise) and for
each ring-internal matching, record the matched color.

For canonical-E2 boards we expect:
  - exactly 60 ring-internal matchings
  - exactly 12 of each rare color (1..5)
  - other colors only appear in: (a) the 4 corner-corner positions (none
    exist; corners join via edge pieces), (b) really shouldn't appear
  - sum of rare colors = 60, of which exactly 12 of each

Run on all 82 boards, print summary per board sorted by score.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


W = H = 16
BORDER = 0
RARE = {1, 2, 3, 4, 5}


def load_board(path: Path):
    with open(path) as f:
        b = json.load(f)
    url = b.get('url', '')
    m = re.search(r'board_edges=([a-z]+)', url)
    if not m:
        return None
    blob = m.group(1)
    if len(blob) < W * H * 4:
        return None
    quads = []
    for pos in range(W * H):
        c = blob[pos*4:pos*4+4]
        quads.append(tuple(ord(ch) - ord('a') for ch in c))
    return {
        'quads': quads,
        'puzzle': b.get('puzzle'),
        'interior_matched': b.get('interior_matched'),
        'pieces_placed': b.get('pieces_placed'),
        'name': path.name,
    }


def ring_internal_matchings(quads):
    """Return the 60 ring-internal matched colors for the given board.

    The border ring consists of 60 cells (top row, right col, bottom row,
    left col — minus 4 double-counted corners). Walking clockwise starting
    at (0,0):
      - 16 top-row cells: (0,0) → (0,15)
      - 15 right-col cells: (1,15) → (15,15)
      - 15 bottom-row cells (reversed): (15,14) → (15,0)
      - 14 left-col cells (reversed): (14,0) → (1,0)
      total = 60

    The "ring-internal matchings" are the 60 matchings between
    consecutive cells in this ring (so the ring is a cycle).

    For each consecutive pair (cellA, cellB), the matched color is the
    edge between them.
    """
    ring = []
    for c in range(W):       ring.append((0, c))
    for r in range(1, H):    ring.append((r, W - 1))
    for c in range(W - 2, -1, -1):  ring.append((H - 1, c))
    for r in range(H - 2, 0, -1):   ring.append((r, 0))
    assert len(ring) == 60

    matchings = []
    for i in range(60):
        a = ring[i]
        b = ring[(i + 1) % 60]
        ra, ca = a
        rb, cb = b
        # determine which edge of cell A connects to cell B
        if rb == ra and cb == ca + 1:
            color = quads[ra * W + ca][1]  # E of A
        elif rb == ra and cb == ca - 1:
            color = quads[ra * W + ca][3]  # W of A
        elif rb == ra + 1 and cb == ca:
            color = quads[ra * W + ca][2]  # S of A
        elif rb == ra - 1 and cb == ca:
            color = quads[ra * W + ca][0]  # N of A
        else:
            # Non-adjacent in grid — happens at corner wraps.
            # Corners: (0,15)->(1,15) is south; OK already.
            # (15,15)->(15,14) west.
            # (15,0)->(14,0) north.
            # (1,0)->(0,0) north.
            # All handled above.
            color = -1
        matchings.append(color)
    return matchings


def main():
    corpus = Path('output/community_corpus')
    index_path = corpus / '_index.tsv'
    canonical = []
    with open(index_path) as f:
        next(f)
        for line in f:
            cols = line.rstrip('\n').split('\t')
            score, placed, puzzle = cols[0], cols[1], cols[2]
            json_name = cols[-1]
            # Canonical = the canonical Monckton 5-clue 16x16 (puzzle="Eternity2")
            # only. Excludes E2nc (no-clue Bucas variant), JBlackwood variants,
            # brendan_16x16, 16_16_set_1, etc.
            if puzzle == 'Eternity2':
                canonical.append((int(score), corpus / json_name))
    # Dedup by json name (index has duplicates for some entries)
    seen = set()
    canonical = [(s, p) for (s, p) in canonical if not (p.name in seen or seen.add(p.name))]
    canonical.sort(reverse=True)

    print(f"{'score':>5} {'plc':>4}  rare1 rare2 rare3 rare4 rare5  total_rare  abundant   name")
    print("=" * 95)
    full_summary = []
    for score, path in canonical[:25]:
        b = load_board(path)
        if b is None:
            continue
        matchings = ring_internal_matchings(b['quads'])
        c = Counter(matchings)
        rare_counts = {r: c.get(r, 0) for r in (1, 2, 3, 4, 5)}
        total_rare = sum(rare_counts.values())
        abundant = sum(c[k] for k in c if k > 5)
        full_summary.append((score, b['name'], rare_counts, total_rare, abundant))
        print(f"{score:>5} {b['pieces_placed']:>4}  {rare_counts[1]:>5} {rare_counts[2]:>5} {rare_counts[3]:>5} {rare_counts[4]:>5} {rare_counts[5]:>5}  {total_rare:>10}  {abundant:>8}   {b['name']}")

    # Aggregate by score-bucket: 480 (full solutions), 469 (community ceiling), 467, etc.
    print("\nBy score group (mean over each rare color):")
    from collections import defaultdict
    grp = defaultdict(list)
    for score, name, rc, _, _ in full_summary:
        grp[score].append(rc)
    for s in sorted(grp.keys(), reverse=True):
        lst = grp[s]
        avgs = {r: sum(d[r] for d in lst)/len(lst) for r in (1, 2, 3, 4, 5)}
        print(f"  score {s:>5} ({len(lst)} boards): rare counts ≈ {{1: {avgs[1]:.1f}, 2: {avgs[2]:.1f}, 3: {avgs[3]:.1f}, 4: {avgs[4]:.1f}, 5: {avgs[5]:.1f}}}")


if __name__ == '__main__':
    main()
