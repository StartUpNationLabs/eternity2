#!/usr/bin/env python3
"""Z_22 vertex-charge fingerprint of the 453 board.

X1 agent (vol-7 launch) proposed treating each interior vertex of the
16×16 board as a Z_22 plaquette: the 4 colors meeting at the vertex
sum mod 22 to a topological charge c_v ∈ Z_22.

For a perfect solution: every interior vertex has c_v = 0 (all 4 edges
match, so the 4 colors cancel pairwise around the vertex).

For an imperfect solution: nonzero charges localise at mismatched
vertices. If charges cluster spatially in opposite-sign pairs at small
Manhattan distance, disclination-string moves are viable.

This is also a publishable structural signature regardless of whether
we pursue the disclination move.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

BORDER = 65535
PUZZLE = Path(__file__).parent.parent.parent / "data" / "puzzles" / "size_16_official_eternity.csv"


def parse_color(s):
    v = int(s.strip(), 2)
    return -1 if v == BORDER else v


def load_pieces():
    pieces = []
    with PUZZLE.open() as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    for ln in lines[1:]:
        cols = ln.split(",")
        pieces.append(tuple(parse_color(c) for c in cols[:4]))
    return pieces


def rotate(piece, rot):
    t, r, b, l = piece
    if rot == 0:
        return (t, r, b, l)
    if rot == 1:
        return (l, t, r, b)
    if rot == 2:
        return (b, l, t, r)
    if rot == 3:
        return (r, b, l, t)


def main():
    pieces = load_pieces()
    n = 22  # modulus for Z_22 (22 interior colors)

    boards = [
        ("453 (HISTORIC first)", "output/night-archive/HISTORIC_first_453_1778557672.json"),
        ("453 (xl)",             "output/night-archive/HISTORIC_453_xl_3_1778563900.json"),
        ("453 (cascade)",        "output/night-archive/HISTORIC_453_cascade453_1778559704.json"),
        ("452 (galarge 5)",      "output/night-archive/HISTORIC_452_galarge_5_1778554772.json"),
        ("451 (galarge 17)",     "output/night-archive/HISTORIC_451_galarge_17_1778555853.json"),
    ]

    for name, path in boards:
        try:
            d = json.load(open(path))
        except FileNotFoundError:
            print(f"SKIP missing: {path}")
            continue
        pl = d["placement"]
        W = 16

        # For each interior vertex (intersection of 4 cells), sum the 4
        # colors that meet at it. A vertex (vx, vy) with 0 < vx < 16 and
        # 0 < vy < 16 has the 4 cells:
        #   NW: (vx-1, vy-1) -> bottom-right edges (b, r) of NW cell
        #   NE: (vx,   vy-1) -> bottom-left edges  (b, l) of NE cell
        #   SW: (vx-1, vy)   -> top-right edges    (t, r) of SW cell
        #   SE: (vx,   vy)   -> top-left edges     (t, l) of SE cell
        # Actually the 4 colors at the vertex are the 4 corners of the
        # piece-edges that meet at the vertex.
        # Specifically the vertex is bounded by:
        #   NW cell's right edge color (color of NE-SW segment of NW piece)
        #   NE cell's left  edge color
        #   SW cell's right edge color
        #   SE cell's left  edge color
        # Wait — careful. The vertex is where 4 cells' corners meet.
        # The 4 EDGES incident to the vertex are:
        #   E1 (above): NW cell's right edge = NE cell's left edge
        #     (these should be equal if matched).
        #   E2 (below): SW cell's right edge = SE cell's left edge.
        #   E3 (to the left):  NW cell's bottom edge = SW cell's top edge.
        #   E4 (to the right): NE cell's bottom edge = SE cell's top edge.
        # Each edge has ONE color (it's where two cells meet). So the
        # 4 colors meeting at the vertex are E1.color, E2.color,
        # E3.color, E4.color.
        # The "Z_22 charge" is sum mod 22.

        def cell_edges(idx):
            e = pl[idx]
            pid, rot = e["piece_id"], e["rotation"]
            return rotate(pieces[pid], rot)  # (t, r, b, l)

        charges = {}
        for vy in range(1, W):
            for vx in range(1, W):
                # 4 cells around vertex (vx, vy):
                nw_idx = (vy - 1) * W + (vx - 1)
                ne_idx = (vy - 1) * W + vx
                sw_idx = vy * W + (vx - 1)
                se_idx = vy * W + vx

                _, nw_r, nw_b, _ = cell_edges(nw_idx)
                _, _, ne_b, ne_l = cell_edges(ne_idx)
                sw_t, sw_r, _, _ = cell_edges(sw_idx)
                se_t, _, _, se_l = cell_edges(se_idx)

                # 4 edges incident to vertex:
                # E1 (top horizontal segment, between NW and NE cell):
                #    NW.right - NE.left  (sign: + - = 0 if matched)
                # E2 (bottom horizontal segment, between SW and SE):
                #    SW.right - SE.left
                # E3 (left vertical segment, between NW and SW):
                #    NW.bottom - SW.top
                # E4 (right vertical segment, between NE and SE):
                #    NE.bottom - SE.top
                #
                # If all 4 edges are matched, each delta = 0 and charge = 0.
                # For a mismatched vertex, charge is sum of deltas mod 22.

                # Use mod-22 arithmetic on color labels.
                # The 4 colors as ints, treating BORDER (-1) as undefined.
                # We only check INTERIOR vertices (vx,vy both in [1, W-1]),
                # where all 4 surrounding cells have interior edges meeting
                # at the vertex.

                # Compute the four edge-COLOR differences
                d1 = (nw_r - ne_l) % n
                d2 = (sw_r - se_l) % n
                d3 = (nw_b - sw_t) % n
                d4 = (ne_b - se_t) % n
                # Total "charge" at the vertex:
                c = (d1 + d2 + d3 + d4) % n
                charges[(vx, vy)] = (c, d1, d2, d3, d4)

        # Stats
        nonzero = [(v, c[0]) for v, c in charges.items() if c[0] != 0]
        print(f"\n=== {name} ===")
        print(f"  interior vertices: {len(charges)}")
        print(f"  nonzero charges: {len(nonzero)} ({len(nonzero) / len(charges):.1%})")
        # By charge value
        charge_hist = Counter(c[0] for c in charges.values())
        print(f"  charge distribution: {dict(sorted(charge_hist.items()))}")

        # Spatial clustering: average L1 distance between opposite-sign pairs
        # In Z_22, "opposite-sign" of c is (n - c) % n. Skip 0.
        positives = [(v, c[0]) for v, c in charges.items() if 0 < c[0] < n // 2 + 1]
        negatives = [(v, c[0]) for v, c in charges.items() if c[0] > n // 2]
        print(f"  positive charges (1..11): {len(positives)}")
        print(f"  negative charges (12..21): {len(negatives)}")

        # For each positive charge p at v_p, find the NEAREST opposite
        # (n - p) at any vertex v_q. Manhattan distance.
        opp_distances = []
        for vp, cp in positives:
            opp = (n - cp) % n
            best_dist = None
            for vq, cq in charges.items():
                if cq[0] == opp:
                    dist = abs(vp[0] - vq[0]) + abs(vp[1] - vq[1])
                    if dist > 0 and (best_dist is None or dist < best_dist):
                        best_dist = dist
            if best_dist is not None:
                opp_distances.append(best_dist)
        if opp_distances:
            import statistics
            print(f"  opposite-charge nearest-pair distances (n={len(opp_distances)}):")
            print(f"    mean {statistics.mean(opp_distances):.2f}  median {statistics.median(opp_distances)}  min {min(opp_distances)}  max {max(opp_distances)}")

        # Print spatial map of charges (0 = '.', nonzero = single hex digit)
        print(f"  spatial charge map (rows 1..15, cols 1..15):")
        for vy in range(1, W):
            row = ""
            for vx in range(1, W):
                c, _, _, _, _ = charges[(vx, vy)]
                row += "." if c == 0 else (str(c) if c < 10 else chr(ord('a') + c - 10))
            # Mark hint position approx
            marker = " *" if vy == 8 else ""
            print(f"    {vy:2d} {row}{marker}")


if __name__ == "__main__":
    main()
