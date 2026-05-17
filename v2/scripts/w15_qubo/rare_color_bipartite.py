"""Vol-124+ derivation: rare-color bipartite matching on the border ring.

Every border/corner piece (60 of them) has at least one rare color (2-6).
In a 480 solution, the perimeter ring has 60 internal-side edges (between
the border and adjacent interior pieces) plus 60 ring-side edges (between
adjacent border pieces). The ring-side edges are colored by the rare-color
edges of adjacent border pieces.

QUESTION: How many DIFFERENT 60-piece border rings (color-matched on
the ring side) exist? This is a bipartite-matching / Hamiltonian-cycle
problem on a small graph.

A 60-piece border ring exists ⟺ we can arrange the 60 border pieces in a
cyclic sequence such that consecutive pieces' adjacent rare-color edges match.

For 60 pieces, each with on average 2 rare edges, the ring is a small CSP.
Let's enumerate it.
"""

from __future__ import annotations
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import load_puzzle, BORDER

W = 16
RARE = {2, 3, 4, 5, 6}


def main():
    p = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))
    print(f"Puzzle: {p.size}x{p.size}, {p.n_colors} colors")

    # Classify pieces
    corners = []  # 2 border edges
    edges = []    # 1 border edge
    interiors = []
    for pid in range(p.n_pieces):
        e = p.piece_edges(pid, 0)
        n_border = sum(1 for c in e if c == BORDER)
        if n_border == 2: corners.append(pid)
        elif n_border == 1: edges.append(pid)
        else: interiors.append(pid)
    print(f"Corners: {len(corners)}, Edges: {len(edges)}, Interiors: {len(interiors)}")

    # For each edge piece + rotation putting border-side OUT, find the
    # (left-rare, right-rare, in-color) tuple.
    # In canonical orientation: BORDER on N → rotation with N=BORDER.
    # Then ring-side colors are W and E. Inside-side is S.
    print("\nEnumerating border edge pieces (60 - 4 = 56 of them):")
    edge_ring_data = []  # list of (pid, rotation, west_color, east_color, south_color)
    for pid in edges:
        for r in range(4):
            n, e, s, w = p.piece_edges(pid, r)
            if n == BORDER:  # canonical: border-side north (top row)
                edge_ring_data.append((pid, r, w, e, s, "T"))
        # Also need rotations putting BORDER on E (right column), S (bottom), W (left)
        # For now we focus on the abstract graph: each edge piece has 2 rare colors
        # on its 2 non-border, non-interior sides (left/right when border is "out").

    # Print first few
    for d in edge_ring_data[:10]:
        print(f"  piece {d[0]} rot {d[1]} pos=T: W={d[2]} E={d[3]} S(in)={d[4]}")
    print(f"\nTotal top-side edge orientations: {len(edge_ring_data)}")
    # Wait — there's some rotational redundancy. Let me count distinct (pid, "top") combinations
    distinct = set((d[0], d[5]) for d in edge_ring_data)
    print(f"Distinct (piece, position-class): {len(distinct)}")

    # Now build the bipartite ring problem more concretely.
    # Per row 0 of the 4-color top-side rotated set:
    print("\nFor pieces with BORDER on N (top-row orientation):")
    # Group by (left-rare, right-rare) pair
    pair_count = defaultdict(int)
    for d in edge_ring_data:
        pid, r, w, e, s, pos = d
        # w and e should both be in RARE (vol-7: rare colors only on border ring sides)
        if w in RARE and e in RARE:
            pair_count[(w, e)] += 1
        else:
            pass  # exception case
    print(f"\nRare-rare (W, E) pair frequencies on top-side orientation:")
    for (w, e), n in sorted(pair_count.items()):
        print(f"  ({w}, {e}): {n} pieces")

    # The TOP edge of the puzzle has 14 edge pieces between corners.
    # The ring graph: vertices = rare colors {2,3,4,5,6}, edges = "this piece connects W to E".
    # We need a walk of length 14 from some color to some color, using 14 DISTINCT pieces.
    # The corners on the top side fix the starting color (TL corner's E-rare-color)
    # and ending color (TR corner's W-rare-color).

    # Corner analysis: each corner piece has 2 border edges + 2 non-border edges.
    # In TL position (N=BORDER, W=BORDER), the non-border sides are E and S.
    # E goes to the next piece on top row (so E is rare).
    # S goes to the piece below on left column (so S is rare).
    print("\nCorner pieces:")
    for pid in corners:
        for r in range(4):
            n, e, s, w = p.piece_edges(pid, r)
            if n == BORDER and w == BORDER:
                print(f"  piece {pid} TL-rot{r}: E={e}, S={s}  (both should be rare)")
                break


if __name__ == "__main__":
    main()
