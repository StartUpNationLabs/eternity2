"""Count distinct valid border rings on canonical E2.

A "border ring" is an arrangement of:
  - 4 corner pieces (with rotation pinned by corner-position constraints)
  - 56 edge pieces (each with rotation pinned: border-side faces outward)
in a cyclic order around the perimeter such that adjacent border pieces
have matching rare-color edges.

Specifically:
  - 14 top-row edges + 14 right + 14 bottom + 14 left = 56 edges
  - Plus 4 corners
Total 60 ring positions.

Each edge piece in its "border-out" orientation has a (W, E) rare-color pair.
Each corner piece in its corner-position rotation has a (W, E) rare-color pair
(where W = inside-side facing previous ring position, E = facing next).

The ring is a 60-position cyclic sequence using each piece exactly once,
with consecutive pieces' (E, W) colors matching.

This is a Hamiltonian-cycle count on a 60-vertex graph. Tractable via DP
on rare-color states.
"""

from __future__ import annotations
import sys
from pathlib import Path
from collections import defaultdict
from itertools import permutations

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import load_puzzle, BORDER

W = 16
RARE = {2, 3, 4, 5, 6}


def main():
    p = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))

    # Classify
    corners = []
    edges = []
    for pid in range(p.n_pieces):
        e = p.piece_edges(pid, 0)
        nb = sum(1 for c in e if c == BORDER)
        if nb == 2: corners.append(pid)
        elif nb == 1: edges.append(pid)

    print(f"Corners: {len(corners)} pieces, Edges: {len(edges)} pieces")

    # For each EDGE piece, find its canonical "border-out" rotation and
    # store (W_color, E_color) where the BORDER side is N.
    # Equivalently: when placed on TOP row, what's the (left-neighbor-color,
    # right-neighbor-color) pair?
    edge_to_we = {}
    for pid in edges:
        for r in range(4):
            n, e, s, w = p.piece_edges(pid, r)
            if n == BORDER:
                edge_to_we[pid] = (w, e)
                break

    # For each CORNER piece, store its 4 (W, E) options (one per corner position)
    # But there are only 4 corners and they MUST occupy the 4 corner positions
    # in some permutation. We need:
    #   TL: piece+rotation with N=W=BORDER, contributes E (right) and S (down)
    #   TR: piece+rotation with N=E=BORDER, contributes S (down) and W (left)
    #   BR: piece+rotation with S=E=BORDER, contributes W (left) and N (up)
    #   BL: piece+rotation with S=W=BORDER, contributes N (up) and E (right)
    # Each contributes 2 rare colors.
    corner_data = {}  # pid → {position: (out_w_neighbor, out_e_neighbor)}
    for pid in corners:
        corner_data[pid] = {}
        for r in range(4):
            n, e, s, w = p.piece_edges(pid, r)
            if n == BORDER and w == BORDER:
                # TL: ring goes ... → TL → next-on-top → ...
                # TL's "previous" ring neighbor is the last piece on left column (N=its S)
                # TL's "next" ring neighbor is the first piece on top row (E=its E)
                # On the top row, TL's right ring-edge color = E
                # On the left column, TL's bottom ring-edge color = S
                corner_data[pid]["TL"] = (s, e)  # (prev=down-left, next=right-top)
            elif n == BORDER and e == BORDER:
                corner_data[pid]["TR"] = (w, s)
            elif s == BORDER and e == BORDER:
                corner_data[pid]["BR"] = (n, w)
            elif s == BORDER and w == BORDER:
                corner_data[pid]["BL"] = (e, n)

    print(f"\nCorner data (piece → position → (prev_color, next_color)):")
    for pid, d in corner_data.items():
        for pos, colors in d.items():
            print(f"  piece {pid} as {pos}: prev={colors[0]}, next={colors[1]}")

    # === Count rings via DP ===
    # The ring goes: TL → top_edges (14) → TR → right_edges (14) → BR → bottom_edges (14) → BL → left_edges (14) → TL
    # Each side is a length-14 walk through edge pieces.
    # Total: 4 corner-perms × 14! permutations of top × ... no, much smaller due to color matching.

    # DP on top side: f(i, color, used_set) = # ways to fill first i positions with last-color = color
    # used_set is too big to track. Use INCLUSION-EXCLUSION or accept the count is bounded by 56^14.
    # Better: count IGNORING piece-uniqueness, then bound by 1.

    # Actually the right structure: 56 edges, each contributes one (W,E) pair.
    # For each side (top), we need 14 edges in a walk from start_color to end_color,
    # using 14 DISTINCT pieces.

    # Build the bipartite-edge "type" digest: how many edges of each (W,E) type?
    type_count = defaultdict(int)
    for pid, (w, e) in edge_to_we.items():
        type_count[(w, e)] += 1
    print(f"\nEdge (W, E) type counts: {dict(type_count)}")
    print(f"Distinct types: {len(type_count)}")
    print(f"Total edges: {sum(type_count.values())}")

    # For now just SAMPLE how many top-side rings exist for a fixed corner choice.
    # Pick (TL=0, TR=1, BR=3, BL=2) arbitrarily (one of 24 perms).
    print("\n--- ONE CORNER PERMUTATION SAMPLE ---")
    tl_pid, tr_pid, br_pid, bl_pid = 0, 1, 3, 2
    print(f"TL={tl_pid}, TR={tr_pid}, BR={br_pid}, BL={bl_pid}")
    if "TL" not in corner_data[tl_pid] or "TR" not in corner_data[tr_pid] \
       or "BR" not in corner_data[br_pid] or "BL" not in corner_data[bl_pid]:
        print("  invalid: a corner piece can't take its assigned position.")
        return

    tl_d = corner_data[tl_pid]["TL"]
    tr_d = corner_data[tr_pid]["TR"]
    print(f"  Top row: needs walk from color={tl_d[1]} to color={tr_d[0]} (length 14, distinct edges)")
    # Count length-14 walks ignoring distinctness for upper bound:
    # Build digraph: vertex=color, edge=(W,E) -> "count" labeled with set of pieces.
    out_edges = defaultdict(lambda: defaultdict(list))  # out_edges[from_color][to_color] = list of (pid)
    for pid, (w, e) in edge_to_we.items():
        out_edges[w][e].append(pid)

    # DP on length-14 walks from start to end (no piece dedup for upper bound)
    start = tl_d[1]
    end = tr_d[0]
    # f[step][color] = # walks of length `step` ending at color
    f = {c: 0 for c in {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23}}
    f[start] = 1
    for step in range(14):
        nf = {c: 0 for c in f}
        for c in f:
            if f[c] == 0: continue
            for c2, pids in out_edges.get(c, {}).items():
                nf[c2] += f[c] * len(pids)
        f = nf
    print(f"  # length-14 walks (ignoring distinctness): {f.get(end, 0):,}")
    print(f"  Note: real ring count is bounded ABOVE by this number.")


if __name__ == "__main__":
    main()
