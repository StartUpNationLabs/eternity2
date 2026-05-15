#!/usr/bin/env python3
"""Vol-72 — NS-1 Δ-invariant on our 2 unique 469 boards.

The Hopfer 2022 NS-1 invariant: for valid 480 solutions, multiset
of inward-facing border colors = multiset of border-facing interior
colors. Δ = (sum |A[c] - B[c]| / 2) counts border-interior mismatches.

Vol-11 measured Δ ∈ {0,1} on canonical-E2 469s (one board only).

Now we have 2 distinct 469 boards. Test if BOTH have Δ ∈ {0,1}.
Also: what's the Δ-distribution across our 4 high-score basins?
"""

import collections
import csv
import json
from pathlib import Path


def load_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append((col(parts[0]), col(parts[1]), col(parts[2]), col(parts[3])))
    return pieces


def rotate(edges, k):
    n, e, s, w = edges
    if k == 0: return (n, e, s, w)
    if k == 1: return (w, n, e, s)
    if k == 2: return (s, w, n, e)
    if k == 3: return (e, s, w, n)


def load_placement(path):
    with open(path) as f: d = json.load(f)
    arr = d.get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        out[pos] = (item["piece_id"], item["rotation"])
    return out, d.get("matched")


def compute_delta(placement, pieces):
    """NS-1 Δ: multiset of border-piece's inward colors vs perimeter-interior cells' border-facing colors.

    Border cells (perimeter cells, pos in {0..15, 240..255, 0,16,32,...240, 15,31,47,...255}):
      - In row 0: border-facing-out is N (top); inward-facing-in is S
      - In col 0: border-facing-out is W; inward is E
      - In row 15: border-out is S; inward is N
      - In col 15: border-out is E; inward is W
    The "inward" multiset = colors of border-piece's side facing interior.

    Perimeter-of-interior cells (cells in row 1, 14 or col 1, 14, EXCLUDING the cells already in border):
      Their border-facing side (toward perimeter) is N/E/S/W depending on position.

    NS-1 says these two multisets are equal in any valid assembly.
    """
    inward_border = collections.Counter()  # border pieces' inward colors
    border_facing_interior = collections.Counter()  # interior-perim cells' colors facing border

    W = 16
    for pos, (pid, rot) in placement.items():
        r, c = divmod(pos, W)
        edges = rotate(pieces[pid], rot)  # N, E, S, W
        # Border cells: r == 0 or r == 15 or c == 0 or c == 15
        is_border = (r == 0 or r == 15 or c == 0 or c == 15)
        if is_border:
            # The "inward" side(s)
            if r == 0: inward_border[edges[2]] += 1  # S faces interior
            if r == 15: inward_border[edges[0]] += 1  # N faces interior
            if c == 0: inward_border[edges[1]] += 1  # E faces interior
            if c == 15: inward_border[edges[3]] += 1  # W faces interior
        else:
            # Interior cells: check if they are perimeter-of-interior (one off the actual border)
            if r == 1: border_facing_interior[edges[0]] += 1  # N faces border
            if r == 14: border_facing_interior[edges[2]] += 1  # S faces border
            if c == 1: border_facing_interior[edges[3]] += 1  # W faces border
            if c == 14: border_facing_interior[edges[1]] += 1  # E faces border

    # Δ = sum |A[c] - B[c]| / 2
    all_colors = set(inward_border.keys()) | set(border_facing_interior.keys())
    delta = 0
    for c in all_colors:
        delta += abs(inward_border[c] - border_facing_interior[c])
    delta //= 2
    return delta, dict(inward_border), dict(border_facing_interior)


def main():
    pieces = load_pieces()

    paths = [
        ("McGavin-469", "output/vol-65/mcgavin_469.json"),
        ("NEW-469-near-twin", "output/vol-68/NEW_469_BOARDS/NEW_469_swap_pieces_234_235_at_pos_73_75.json"),
        ("local-459-p06", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"),
        ("vol-32-458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"),
        ("vol-61-s17", "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json"),
        ("vol-61-s200", "output/vol-61/faithful_sota_20260515T174124/stage3_seed200.json"),
    ]
    for name, path in paths:
        if not Path(path).exists():
            print(f"{name}: missing")
            continue
        pl, sc = load_placement(path)
        delta, A, B = compute_delta(pl, pieces)
        print(f"{name} (score {sc}): Δ = {delta}")
        # Show non-zero diffs
        diff_colors = sorted(set(A.keys()) | set(B.keys()))
        nonzero = [c for c in diff_colors if A.get(c, 0) != B.get(c, 0)]
        if nonzero:
            print(f"  diff colors:")
            for c in nonzero[:5]:
                print(f"    color {c}: border-inward={A.get(c, 0)}, interior-perim-facing={B.get(c, 0)}")


if __name__ == "__main__":
    main()
