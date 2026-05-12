#!/usr/bin/env python3
"""Verhaard piece valuation by 2×3 tileability.

For each of the 256 pieces, count the number of valid 2×3 sub-tilings
(2 columns × 3 rows, with the two top corners being border pieces) in
which the piece appears. Pieces with high frequency are "precious";
pieces with low/zero frequency are "useless".

Algorithm (Verhaard, eii_details.html):

  A 2×3 sub-tiling is a placement of 6 pieces in a 2×3 grid (let's
  say columns x = 0, 1; rows y = 0, 1, 2). With the top row (y=0)
  positions being on the board's top edge: those two pieces must have
  BORDER on their top edges (= they are corner or edge pieces of E2).

  Validity: all internal edges must color-match. External edges (left
  of (0,0), right of (1,0), left of (0,1), etc.) can be anything.

  For each piece P, count the number of (rotation, position-in-the-2×3)
  combos such that P participates in some valid full 2×3 tiling.

Output: per-piece "tileability count". Bucket pieces into 4 tiers
(useless / bad / good / precious) at percentile cut-points.
"""

import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

BORDER = 65535
PUZZLE = Path(__file__).parent.parent.parent / "data" / "puzzles" / "size_16_official_eternity.csv"


def parse_color(s):
    v = int(s.strip(), 2)
    return -1 if v == BORDER else v


def load_pieces():
    """Return (n_size, list of (top, right, bottom, left) for each piece, ids)."""
    pieces = []
    with PUZZLE.open() as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    size = int(lines[0])
    for ln in lines[1:]:
        cols = ln.split(",")
        top, right, bottom, left = (parse_color(c) for c in cols[:4])
        pieces.append((top, right, bottom, left))
    return size, pieces


def rotate(piece, rot):
    """Return (t, r, b, l) after rot quarter-turns CCW."""
    t, r, b, l = piece
    if rot == 0:
        return (t, r, b, l)
    if rot == 1:
        return (l, t, r, b)
    if rot == 2:
        return (b, l, t, r)
    if rot == 3:
        return (r, b, l, t)
    raise ValueError(rot)


def piece_class(piece):
    """corner if 2 borders; edge if 1; interior if 0."""
    borders = sum(1 for c in piece if c == -1)
    if borders == 2:
        return "corner"
    if borders == 1:
        return "edge"
    if borders == 0:
        return "interior"
    return "??"


def main():
    size, pieces = load_pieces()
    n = len(pieces)
    print(f"loaded {n} pieces", file=sys.stderr)

    # Index pieces by class for fast iteration
    corner_ids = [i for i, p in enumerate(pieces) if piece_class(p) == "corner"]
    edge_ids = [i for i, p in enumerate(pieces) if piece_class(p) == "edge"]
    interior_ids = [i for i, p in enumerate(pieces) if piece_class(p) == "interior"]
    print(f"corners {len(corner_ids)} edges {len(edge_ids)} interior {len(interior_ids)}", file=sys.stderr)

    # 2×3 layout (2 wide, 3 tall):
    #   (0,0)  (1,0)    <- both on board's top edge => need BORDER on top
    #   (0,1)  (1,1)
    #   (0,2)  (1,2)
    # External edges:
    #   left of column 0  (could be any color OR border)
    #   right of column 1 (could be any color OR border)
    # Internal edges:
    #   (0,0).right = (1,0).left
    #   (0,0).bottom = (0,1).top
    #   (1,0).bottom = (1,1).top
    #   (0,1).right = (1,1).left
    #   (0,1).bottom = (0,2).top
    #   (1,1).bottom = (1,2).top
    #   (0,2).right = (1,2).left
    # External: (0,0).top must be border; (1,0).top must be border; bottoms
    # of (0,2) and (1,2) can be anything; left/right edges can be anything.
    # Actually Verhaard's setup is "with two border pieces"; the most
    # natural reading is the top-row pieces have BORDER on top (they could
    # be corner pieces or edge pieces along the top of the puzzle).

    # Precompute per-piece-rotation tuples:
    # rots[pid][rot] = (t, r, b, l)
    rots = [[rotate(p, r) for r in range(4)] for p in pieces]

    # Tileability count per piece (sum over rotation × position-in-2×3)
    tileability = [0] * n
    start = time.time()

    # Iterate over all valid 6-tuple piece selections.
    # 256 ** 6 = 2.8e14 — way too many. We must use color-match propagation.
    # Strategy: place pieces left-to-right, top-to-bottom; prune by color
    # match at each step.
    #
    # For "with two border pieces" interpretation: the top row (positions
    # (0,0), (1,0)) must have BORDER on top. Restrict those positions to
    # corner + edge pieces.

    # We use 6 nested loops with pruning. The key invariant: at each step
    # we know the constraints on the next piece (must color-match the
    # already-placed adjacent edges).

    # Build index: for each piece-rotation, what is the (top, right, bottom, left)
    # signature?
    # And: for given required (top_color, left_color), which (piece, rot) match?
    # Build only over "non-corner border-top" pieces for top row: piece must
    # have BORDER on its top edge after rotation.

    # Tabulate piece pools:
    # - top_row pool: piece-rotations where rotated-top = BORDER.
    # - body pool: any piece-rotation (could be corner, edge, interior; but
    #   for legit 2×3 placement, the body row positions (0,1)..(1,2) could
    #   accept any piece. In a real board's interior, body positions need
    #   pieces without BORDER on their relevant edges — but in this 2×3
    #   PIECE-VALUATION sub-tiling, we count over ALL valid color-matched
    #   6-tuples regardless of where the 2×3 would actually live on the
    #   board.
    # Verhaard's definition might be more restrictive (e.g., body row
    # pieces are interior); but using the broader count gives a valuation
    # signal anyway.

    # CORRECTED INTERPRETATION (per Verhaard's wording "with two border
    # pieces"): the top row of the 2×3 are border-pieces (corner or edge
    # pieces with rotated-top = BORDER); the body row positions are
    # restricted to INTERIOR pieces (no BORDER on any edge). This gives a
    # valuation that meaningfully distinguishes interior pieces, instead
    # of being dominated by edge-piece counts.
    top_pool = []  # list of (pid, rot, t, r, b, l) — must have rotated-top = BORDER
    body_pool = []  # interior pieces only
    for pid in range(n):
        cls = piece_class(pieces[pid])
        for rot in range(4):
            t, r, b, l = rots[pid][rot]
            row = (pid, rot, t, r, b, l)
            if cls == "interior":
                body_pool.append(row)
            if t == -1:  # border pieces with rotation giving BORDER on top
                top_pool.append(row)

    print(f"top_pool {len(top_pool)} body_pool {len(body_pool)}", file=sys.stderr)

    # Index body_pool by (top_color, left_color) for fast lookup when we
    # know both constraints.
    # left_color = -1 means "left edge unconstrained" (column 0) — only
    # constrain via the relevant axis.
    # For our 2×3: column-0 positions have unconstrained left; column-1
    # positions have left = column-0-piece's right.
    body_by_top = {}
    body_by_top_left = {}
    for pid, rot, t, r, b, l in body_pool:
        body_by_top.setdefault(t, []).append((pid, rot, t, r, b, l))
        body_by_top_left.setdefault((t, l), []).append((pid, rot, t, r, b, l))

    # Top-row positions can be ANY piece with BORDER top. Column-0 has
    # unconstrained left; column-1 has left = column-0-piece's right.
    top_by_left = {}
    for pid, rot, t, r, b, l in top_pool:
        top_by_left.setdefault(l, []).append((pid, rot, t, r, b, l))

    # Algorithm: enumerate over (p00, p10, p01, p11, p02, p12) with
    # color-match pruning. Avoid double-counting piece-uniqueness:
    # for the valuation count, we should count each (piece, rot, position)
    # only when the OTHER 5 pieces are DISTINCT and valid.

    # Counts: 6 positions × ~60 (top corners/edges) × ~1024 (body) = could
    # blow up. Let's count without the alldiff first, see if signal is
    # already there. Then add alldiff.

    n_tilings = 0
    progress = 0

    # IMPORTANT: enforce alldiff (each piece used at most once in the 6-tuple).
    # Otherwise the count is dominated by pieces that appear many times.
    for (pid00, rot00, t00, r00, b00, l00) in top_pool:
        progress += 1
        if progress % 25 == 0:
            print(f"top0 progress {progress}/{len(top_pool)}", file=sys.stderr)
        # Position (1,0): top must be -1, left must = r00
        for (pid10, rot10, t10, r10, b10, l10) in top_by_left.get(r00, []):
            if pid10 == pid00:
                continue
            # Position (0,1): top must = b00
            for (pid01, rot01, t01, r01, b01, l01) in body_by_top.get(b00, []):
                if pid01 in (pid00, pid10):
                    continue
                # Position (1,1): top = b10, left = r01
                for (pid11, rot11, t11, r11, b11, l11) in body_by_top_left.get((b10, r01), []):
                    if pid11 in (pid00, pid10, pid01):
                        continue
                    # Position (0,2): top = b01
                    for (pid02, rot02, t02, r02, b02, l02) in body_by_top.get(b01, []):
                        if pid02 in (pid00, pid10, pid01, pid11):
                            continue
                        # Position (1,2): top = b11, left = r02
                        for (pid12, rot12, t12, r12, b12, l12) in body_by_top_left.get((b11, r02), []):
                            if pid12 in (pid00, pid10, pid01, pid11, pid02):
                                continue
                            n_tilings += 1
                            # Count each piece's appearance
                            tileability[pid00] += 1
                            tileability[pid10] += 1
                            tileability[pid01] += 1
                            tileability[pid11] += 1
                            tileability[pid02] += 1
                            tileability[pid12] += 1

    elapsed = time.time() - start
    print(f"\ntotal 2×3 tilings: {n_tilings:,}  ({elapsed:.1f}s)", file=sys.stderr)

    # Report tileability stats
    print("\npiece tileability (top 20 + bottom 20):", file=sys.stderr)
    indexed = list(enumerate(tileability))
    indexed.sort(key=lambda x: -x[1])
    print(f"\ntop 20 most-tileable pieces:")
    for pid, c in indexed[:20]:
        cls = piece_class(pieces[pid])
        print(f"  piece {pid:3d} ({cls:8s}) {pieces[pid]}: {c:,}")
    print(f"\nbottom 20 least-tileable pieces:")
    for pid, c in indexed[-20:]:
        cls = piece_class(pieces[pid])
        print(f"  piece {pid:3d} ({cls:8s}) {pieces[pid]}: {c:,}")

    # Histogram
    import statistics
    nonzero = [c for c in tileability if c > 0]
    print(f"\ntileability stats: total {sum(tileability):,}; nonzero pieces {len(nonzero)}; zero pieces {n - len(nonzero)}")
    if nonzero:
        print(f"  mean {statistics.mean(nonzero):.0f} median {statistics.median(nonzero):,} stdev {statistics.pstdev(nonzero):.0f}")
        print(f"  min {min(nonzero):,} max {max(nonzero):,}")

    # 4-tier bucket cut points: use 25/50/75 percentiles of nonzero counts
    sorted_nz = sorted(nonzero)
    if sorted_nz:
        q1 = sorted_nz[len(sorted_nz) // 4]
        q2 = sorted_nz[len(sorted_nz) // 2]
        q3 = sorted_nz[3 * len(sorted_nz) // 4]
        print(f"\n4-tier cut points: q1={q1:,} q2={q2:,} q3={q3:,}")
        useless = [pid for pid, c in enumerate(tileability) if c == 0]
        bad = [pid for pid, c in enumerate(tileability) if 0 < c <= q1]
        good = [pid for pid, c in enumerate(tileability) if q1 < c <= q3]
        precious = [pid for pid, c in enumerate(tileability) if c > q3]
        print(f"  useless: {len(useless)} pieces")
        print(f"  bad:     {len(bad)} pieces")
        print(f"  good:    {len(good)} pieces")
        print(f"  precious:{len(precious)} pieces")

        # Save valuations
        out = {
            "metric": "2x3 tileability (alldiff)",
            "n_tilings": n_tilings,
            "tileability": tileability,
            "tiers": {
                "useless": useless,
                "bad": bad,
                "good": good,
                "precious": precious,
            },
            "cut_points": {"q1": q1, "q2": q2, "q3": q3},
        }
        outpath = "scripts/verhaard_valuation_output.json"
        with open(outpath, "w") as f:
            json.dump(out, f)
        print(f"\nwrote {outpath}", file=sys.stderr)


if __name__ == "__main__":
    main()
