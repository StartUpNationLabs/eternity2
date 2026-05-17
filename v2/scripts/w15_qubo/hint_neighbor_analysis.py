"""Vol-124 hint-neighbor deduction.

For each of the 5 canonical hints, find which pieces can validly be placed
at each of its 4 neighbors. If any neighbor has domain size 1, we have
a forced placement.

In a 480 solution:
  - Each hint has a specific piece+rotation pinned.
  - That piece exposes specific colors on its N/E/S/W edges.
  - The neighboring cell's adjacent-side color MUST match.
  - Combined with cell-class constraints (corner/edge/interior),
    the candidate set per neighbor is often small.

Forced placements are GOLD: they propagate further deductions.
"""
from __future__ import annotations
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import load_puzzle, BORDER

W = 16
HINTS = {135: (138, 0), 210: (180, 1), 34: (207, 1), 221: (248, 2), 45: (254, 1)}


def main():
    p = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))

    # For each hint, compute its 4 outgoing edge colors after rotation
    for hint_pos, (hint_pid, hint_rot) in HINTS.items():
        hr = hint_pos // W; hc = hint_pos % W
        edges = p.piece_edges(hint_pid, hint_rot)
        n_c, e_c, s_c, w_c = edges
        print(f"\nHint at pos {hint_pos} (row={hr}, col={hc}): piece {hint_pid} rot {hint_rot}")
        print(f"  Edges: N={n_c}, E={e_c}, S={s_c}, W={w_c}")

        # For each direction, find candidate piece-rotations at the neighbor cell.
        # Direction: (dr, dc, my_side_outward, their_side_facing_me)
        directions = [
            ("N", -1, 0, n_c, 2),  # neighbor north: their S must match my N
            ("E", 0, 1, e_c, 3),
            ("S", 1, 0, s_c, 0),
            ("W", 0, -1, w_c, 1),
        ]
        for (name, dr, dc, color, their_side) in directions:
            nr, nc = hr + dr, hc + dc
            if not (0 <= nr < W and 0 <= nc < W):
                print(f"  {name}: outside board")
                continue
            npos = nr * W + nc
            # Determine neighbor cell's class
            is_corner = (nr == 0 or nr == W-1) and (nc == 0 or nc == W-1)
            is_edge = (nr in (0, W-1) or nc in (0, W-1)) and not is_corner
            cell_class = "corner" if is_corner else ("edge" if is_edge else "interior")
            # Find candidate (piece, rot) for npos: piece-class matches cell-class,
            # border-sides correct, AND piece's `their_side` after rotation == color
            candidates = []
            for pid in range(p.n_pieces):
                if pid == hint_pid: continue  # piece already used
                e0 = p.piece_edges(pid, 0)
                n_border = sum(1 for c in e0 if c == BORDER)
                pclass = "corner" if n_border == 2 else ("edge" if n_border == 1 else "interior")
                if pclass != cell_class: continue
                for r in range(4):
                    e = p.piece_edges(pid, r)
                    # Border constraints on neighbor cell's outside sides
                    ok = True
                    if nr == 0 and e[0] != BORDER: ok = False
                    if nr == W-1 and e[2] != BORDER: ok = False
                    if nc == 0 and e[3] != BORDER: ok = False
                    if nc == W-1 and e[1] != BORDER: ok = False
                    # Border constraints on interior sides
                    if nr != 0 and e[0] == BORDER: ok = False
                    if nr != W-1 and e[2] == BORDER: ok = False
                    if nc != 0 and e[3] == BORDER: ok = False
                    if nc != W-1 and e[1] == BORDER: ok = False
                    if not ok: continue
                    # Color match
                    if e[their_side] != color: continue
                    candidates.append((pid, r))
            print(f"  {name} → pos {npos} (row={nr}, col={nc}, {cell_class}): "
                  f"{len(candidates)} candidates with side={color}")
            if 1 <= len(candidates) <= 5:
                for c in candidates:
                    print(f"      piece {c[0]} rot {c[1]}")


if __name__ == "__main__":
    main()
