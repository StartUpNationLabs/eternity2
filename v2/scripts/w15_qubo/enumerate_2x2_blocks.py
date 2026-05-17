"""W14 — Enumerate all internally-matched 2×2 piece blocks on canonical E2.

Each 2×2 block consists of 4 pieces at positions:
  TL  TR
  BL  BR

with 4 rotations each. For the block to be "internally matched":
  - TL's E edge matches TR's W edge
  - TL's S edge matches BL's N edge
  - TR's S edge matches BR's N edge
  - BL's E edge matches BR's W edge

We enumerate ALL distinct (TL_pid, TL_rot, TR_pid, TR_rot, BL_pid, BL_rot,
BR_pid, BR_rot) quadruples meeting these constraints, with all 4 piece ids
distinct (alldiff within the block).

This is the FOUNDATION for the 2x2 super-block QUBO (Bourreau 2020 idea).
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from itertools import combinations
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import load_puzzle, BORDER


def enumerate_blocks(puzzle, super_cell_position: str = "interior"):
    """Enumerate all internally-matched 2×2 blocks consistent with a given
    super-cell position. Position determines which sides must be BORDER:
      - 'tl_corner' : TL's N & W = BORDER; BR has no BORDER constraints
      - 'tr_corner' : TR's N & E = BORDER
      - 'bl_corner' : BL's S & W = BORDER
      - 'br_corner' : BR's S & E = BORDER
      - 't_edge'    : TL.N = TR.N = BORDER, no other constraints
      - 'r_edge'    : TR.E = BR.E = BORDER
      - 'b_edge'    : BL.S = BR.S = BORDER
      - 'l_edge'    : TL.W = BL.W = BORDER
      - 'interior'  : NO side has BORDER
    """
    n_pieces = puzzle.n_pieces

    # Pre-compute all (pid, rot, edges) for fast lookup
    all_rots = []
    for pid in range(n_pieces):
        for rot in range(4):
            all_rots.append((pid, rot, puzzle.piece_edges(pid, rot)))

    # Constraint dictionaries based on super-cell position
    def tl_constraint(edges):
        n, e, s, w = edges
        if super_cell_position == "tl_corner":
            return n == BORDER and w == BORDER
        elif super_cell_position == "t_edge":
            return n == BORDER and w != BORDER
        elif super_cell_position == "l_edge":
            return w == BORDER and n != BORDER
        else:
            return n != BORDER and w != BORDER

    def tr_constraint(edges):
        n, e, s, w = edges
        if super_cell_position == "tr_corner":
            return n == BORDER and e == BORDER
        elif super_cell_position == "t_edge":
            return n == BORDER and e != BORDER
        elif super_cell_position == "r_edge":
            return e == BORDER and n != BORDER
        else:
            return n != BORDER and e != BORDER

    def bl_constraint(edges):
        n, e, s, w = edges
        if super_cell_position == "bl_corner":
            return s == BORDER and w == BORDER
        elif super_cell_position == "b_edge":
            return s == BORDER and w != BORDER
        elif super_cell_position == "l_edge":
            return w == BORDER and s != BORDER
        else:
            return s != BORDER and w != BORDER

    def br_constraint(edges):
        n, e, s, w = edges
        if super_cell_position == "br_corner":
            return s == BORDER and e == BORDER
        elif super_cell_position == "b_edge":
            return s == BORDER and e != BORDER
        elif super_cell_position == "r_edge":
            return e == BORDER and s != BORDER
        else:
            return s != BORDER and e != BORDER

    # Index pieces by which super-cell position they could fill
    tl_candidates = [(pid, rot, edges) for (pid, rot, edges) in all_rots
                      if tl_constraint(edges)]
    tr_candidates = [(pid, rot, edges) for (pid, rot, edges) in all_rots
                      if tr_constraint(edges)]
    bl_candidates = [(pid, rot, edges) for (pid, rot, edges) in all_rots
                      if bl_constraint(edges)]
    br_candidates = [(pid, rot, edges) for (pid, rot, edges) in all_rots
                      if br_constraint(edges)]

    print(f"  position={super_cell_position}: TL={len(tl_candidates)}, "
          f"TR={len(tr_candidates)}, BL={len(bl_candidates)}, BR={len(br_candidates)}")
    print(f"  raw 4-tuple space: {len(tl_candidates)*len(tr_candidates)*len(bl_candidates)*len(br_candidates):,}")

    # Index TL by its E edge color → list of (pid, rot)
    tl_by_e = defaultdict(list)
    for (pid, rot, edges) in tl_candidates:
        tl_by_e[edges[1]].append((pid, rot, edges))

    # Index TR by its W edge color → list of (pid, rot)
    tr_by_w = defaultdict(list)
    for (pid, rot, edges) in tr_candidates:
        tr_by_w[edges[3]].append((pid, rot, edges))

    # Index BL by its N edge color
    bl_by_n = defaultdict(list)
    for (pid, rot, edges) in bl_candidates:
        bl_by_n[edges[0]].append((pid, rot, edges))

    # Index BR by its N+W edge color jointly
    br_by_nw = defaultdict(list)
    for (pid, rot, edges) in br_candidates:
        br_by_nw[(edges[0], edges[3])].append((pid, rot, edges))

    blocks = []
    t0 = time.time()
    n_checked = 0
    # Iterate: for each color c1 (edge TL-TR), pair TL and TR.
    # Then for each TL, color c2 (TL.S) → BL with N=c2.
    # Then for each (BL, TR), BR has N=TR.S AND W=BL.E.
    for c_lr, tls in tl_by_e.items():
        trs = tr_by_w.get(c_lr, [])
        if not trs:
            continue
        for tl in tls:
            tl_pid, tl_rot, tl_edges = tl
            for tr in trs:
                tr_pid, tr_rot, tr_edges = tr
                if tr_pid == tl_pid:
                    continue
                # Now BL must have N = TL.S
                c_tb_left = tl_edges[2]
                bls = bl_by_n.get(c_tb_left, [])
                for bl in bls:
                    bl_pid, bl_rot, bl_edges = bl
                    if bl_pid == tl_pid or bl_pid == tr_pid:
                        continue
                    # BR must have N = TR.S AND W = BL.E
                    c_tb_right = tr_edges[2]
                    c_lr_bottom = bl_edges[1]
                    brs = br_by_nw.get((c_tb_right, c_lr_bottom), [])
                    for br in brs:
                        br_pid, br_rot, br_edges = br
                        if br_pid in (tl_pid, tr_pid, bl_pid):
                            continue
                        blocks.append((tl_pid, tl_rot, tr_pid, tr_rot,
                                       bl_pid, bl_rot, br_pid, br_rot))
                        n_checked += 1
                        if n_checked % 1000000 == 0:
                            print(f"  found {len(blocks):,} blocks ({n_checked:,} checks, "
                                  f"{time.time()-t0:.0f}s)")

    print(f"  TOTAL blocks for {super_cell_position}: {len(blocks):,} ({time.time()-t0:.1f}s)")
    return blocks


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle",
                    default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--position", default="interior",
                    choices=["tl_corner", "tr_corner", "bl_corner", "br_corner",
                             "t_edge", "r_edge", "b_edge", "l_edge", "interior"])
    ap.add_argument("--all", action="store_true",
                    help="enumerate every super-cell-position class")
    args = ap.parse_args()

    p = load_puzzle(Path(args.puzzle))
    print(f"Puzzle: {p.size}x{p.size}, {p.n_pieces} pieces, {p.n_colors} colors")

    if args.all:
        for pos in ["tl_corner", "tr_corner", "bl_corner", "br_corner",
                    "t_edge", "r_edge", "b_edge", "l_edge", "interior"]:
            enumerate_blocks(p, pos)
    else:
        enumerate_blocks(p, args.position)


if __name__ == "__main__":
    main()
