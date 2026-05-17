"""W14 — Build a 2×2 super-block CSP for canonical Eternity II.

Each super-cell takes one block from its (pruned) alphabet:
  - Super-grid: 8×8 (since 16×16 / 2 = 8×8 super-cells).
  - Super-cell at (sr, sc) covers cells (2*sr, 2*sc), (2*sr, 2*sc+1),
    (2*sr+1, 2*sc), (2*sr+1, 2*sc+1).

For each super-cell, enumerate the 2×2 blocks consistent with:
  - Its position (corner / edge / interior of super-grid)
  - The 5 canonical hint constraints (super-cells (4,3), (6,1), (1,1),
    (6,6), (1,6) have one slot pinned)

Then encode as SAT: one-hot per super-cell + adjacency edge-matches +
global piece-uniqueness alldiff.

This is the W14 mission. Output: a DIMACS CNF that kissat can attack.
"""

from __future__ import annotations
import sys
import time
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import load_puzzle, BORDER

W = 16
SW = W // 2  # super-width: 8


def all_rots(puzzle):
    """Yield (pid, rot, edges) for every (pid, rot)."""
    out = []
    for pid in range(puzzle.n_pieces):
        for rot in range(4):
            out.append((pid, rot, puzzle.piece_edges(pid, rot)))
    return out


def block_position_class(sr, sc):
    """Return position class for a super-cell at (sr, sc) in 8×8 super-grid.

    Returns dict of slot -> set of required-BORDER sides:
      slot ∈ {TL, TR, BL, BR}
      side ∈ {N, E, S, W} (0,1,2,3)
    """
    border = {"TL": set(), "TR": set(), "BL": set(), "BR": set()}
    if sr == 0:
        border["TL"].add(0); border["TR"].add(0)   # N
    if sr == SW - 1:
        border["BL"].add(2); border["BR"].add(2)   # S
    if sc == 0:
        border["TL"].add(3); border["BL"].add(3)   # W
    if sc == SW - 1:
        border["TR"].add(1); border["BR"].add(1)   # E
    return border


def enumerate_blocks_for_supercell(puzzle, sr, sc,
                                    pinned_slot=None, pinned_piece=None,
                                    pinned_rot=None):
    """Enumerate all 2×2 blocks valid for super-cell (sr, sc), respecting:
      - BORDER edge constraints on the outside-facing sides
      - Optional hint pin: one slot must contain piece `pinned_piece` rotation `pinned_rot`

    Returns list of 8-tuples (tl_pid, tl_rot, tr_pid, tr_rot, bl_pid, bl_rot,
                              br_pid, br_rot).
    """
    border_req = block_position_class(sr, sc)

    rots = all_rots(puzzle)

    def slot_filter(slot):
        req_border = border_req[slot]
        # For each side that must be BORDER, the piece's edge at that side
        # (after rotation) must equal BORDER.
        # For each side that must NOT be BORDER (interior side), it must != BORDER.
        all_sides = {0, 1, 2, 3}
        not_border = all_sides - req_border
        out = []
        for (pid, rot, edges) in rots:
            ok = True
            for side in req_border:
                if edges[side] != BORDER:
                    ok = False; break
            if not ok: continue
            for side in not_border:
                if edges[side] == BORDER:
                    ok = False; break
            if not ok: continue
            out.append((pid, rot, edges))
        return out

    tl_cands = slot_filter("TL")
    tr_cands = slot_filter("TR")
    bl_cands = slot_filter("BL")
    br_cands = slot_filter("BR")

    # Apply hint pin: filter the appropriate slot
    if pinned_slot:
        def filt(lst):
            return [(pid, rot, edges) for (pid, rot, edges) in lst
                    if pid == pinned_piece and rot == pinned_rot]
        if pinned_slot == "TL": tl_cands = filt(tl_cands)
        elif pinned_slot == "TR": tr_cands = filt(tr_cands)
        elif pinned_slot == "BL": bl_cands = filt(bl_cands)
        elif pinned_slot == "BR": br_cands = filt(br_cands)

    # Index TL by its E
    tl_by_e = defaultdict(list)
    for it in tl_cands: tl_by_e[it[2][1]].append(it)
    tr_by_w = defaultdict(list)
    for it in tr_cands: tr_by_w[it[2][3]].append(it)
    bl_by_n = defaultdict(list)
    for it in bl_cands: bl_by_n[it[2][0]].append(it)
    br_by_nw = defaultdict(list)
    for it in br_cands: br_by_nw[(it[2][0], it[2][3])].append(it)

    blocks = []
    for c_lr, tls in tl_by_e.items():
        trs = tr_by_w.get(c_lr, [])
        if not trs: continue
        for (tl_pid, tl_rot, tl_edges) in tls:
            for (tr_pid, tr_rot, tr_edges) in trs:
                if tr_pid == tl_pid: continue
                bls = bl_by_n.get(tl_edges[2], [])
                for (bl_pid, bl_rot, bl_edges) in bls:
                    if bl_pid in (tl_pid, tr_pid): continue
                    brs = br_by_nw.get((tr_edges[2], bl_edges[1]), [])
                    for (br_pid, br_rot, br_edges) in brs:
                        if br_pid in (tl_pid, tr_pid, bl_pid): continue
                        blocks.append((tl_pid, tl_rot, tr_pid, tr_rot,
                                       bl_pid, bl_rot, br_pid, br_rot,
                                       tl_edges, tr_edges, bl_edges, br_edges))
    return blocks


def block_outside_edges(block):
    """For a block, return (north_edges, east_edges, south_edges, west_edges)
    where each is a TUPLE of 2 colors (since super-cell boundaries are 2 cells long).

    block = (tl_pid, tl_rot, tr_pid, tr_rot, bl_pid, bl_rot, br_pid, br_rot,
             tl_edges, tr_edges, bl_edges, br_edges)
    Edges as (N, E, S, W) per piece.
    """
    _, _, _, _, _, _, _, _, tl_e, tr_e, bl_e, br_e = block
    # North side: TL.N, TR.N
    n = (tl_e[0], tr_e[0])
    # East side: TR.E, BR.E
    e = (tr_e[1], br_e[1])
    # South side: BL.S, BR.S
    s = (bl_e[2], br_e[2])
    # West side: TL.W, BL.W
    w = (tl_e[3], bl_e[3])
    return n, e, s, w


def block_piece_set(block):
    """Set of piece IDs used in the block."""
    return frozenset((block[0], block[2], block[4], block[6]))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out-summary", default="output/vol-124/w14_super_block_summary.json")
    args = ap.parse_args()

    puzzle = load_puzzle(Path(args.puzzle))
    print(f"Puzzle: {puzzle.size}x{puzzle.size}, {puzzle.n_pieces} pieces")

    # Hints: pos → (pid, rot). Map each to super-cell + slot.
    HINTS = {135: (138, 0), 210: (180, 1), 34: (207, 1),
             221: (248, 2), 45: (254, 1)}
    slot_names = ['TL', 'TR', 'BL', 'BR']
    hint_supercells = {}
    for pos, (pid, rot) in HINTS.items():
        r, c = pos // W, pos % W
        sr, sc = r // 2, c // 2
        slot = slot_names[(r % 2) * 2 + (c % 2)]
        hint_supercells[(sr, sc)] = (slot, pid, rot)
        print(f"  hint pos {pos}: super-cell ({sr},{sc}) slot {slot} piece {pid} rot {rot}")

    print(f"\nEnumerating alphabet per super-cell (8x8 super-grid = 64 super-cells)...")
    alphabet = {}  # (sr, sc) → list of blocks
    sizes = []
    t0 = time.time()
    for sr in range(SW):
        for sc in range(SW):
            t1 = time.time()
            pinned = hint_supercells.get((sr, sc))
            if pinned:
                slot, pid, rot = pinned
                blocks = enumerate_blocks_for_supercell(
                    puzzle, sr, sc,
                    pinned_slot=slot, pinned_piece=pid, pinned_rot=rot
                )
            else:
                blocks = enumerate_blocks_for_supercell(puzzle, sr, sc)
            alphabet[(sr, sc)] = blocks
            sizes.append(((sr, sc), len(blocks)))
            elapsed = time.time() - t1
            tag = ""
            if pinned: tag = f" [HINT: slot {pinned[0]} pid {pinned[1]} rot {pinned[2]}]"
            print(f"  ({sr},{sc}) {len(blocks):>10,} blocks{tag} ({elapsed:.1f}s)")

    total_alphabet = sum(len(b) for b in alphabet.values())
    print(f"\nTotal alphabet across all super-cells: {total_alphabet:,}")
    print(f"Time: {time.time()-t0:.1f}s")

    # Quick analysis
    sizes.sort(key=lambda x: x[1])
    print(f"\nSmallest super-cells: {sizes[:5]}")
    print(f"Largest super-cells: {sizes[-5:]}")
    print(f"Empty super-cells: {sum(1 for s in sizes if s[1] == 0)}")

    Path(args.out_summary).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_summary, "w") as f:
        json.dump({
            "total_alphabet": total_alphabet,
            "per_supercell": {f"{sr},{sc}": len(b) for (sr, sc), b in alphabet.items()},
            "hint_supercells": {f"{sr},{sc}": [s, p, r]
                                 for (sr, sc), (s, p, r) in hint_supercells.items()},
        }, f, indent=2)
    print(f"\nWrote {args.out_summary}")


if __name__ == "__main__":
    main()
