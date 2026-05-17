"""W14 propagation — fast version.

For each super-cell, compute the SET of boundary-tuples it admits on each side.
Propagate AC-3 over these sets: a super-cell's E-side-tuples must be a subset
of (the union of all blocks' E-tuples in its CURRENT block list), which must
match the neighbor's W-side-tuples.

After convergence, re-filter each super-cell's block list ONCE.
"""
from __future__ import annotations
import sys
import time
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import load_puzzle, BORDER

from w14_super_block_attack import (
    W, SW, enumerate_blocks_for_supercell, block_outside_edges
)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--max-iters", type=int, default=10)
    ap.add_argument("--out", default="output/vol-124/w14_propagated_alphabet.json")
    args = ap.parse_args()

    puzzle = load_puzzle(Path(args.puzzle))

    HINTS = {135: (138, 0), 210: (180, 1), 34: (207, 1),
             221: (248, 2), 45: (254, 1)}
    slot_names = ['TL', 'TR', 'BL', 'BR']
    hint_supercells = {}
    for pos, (pid, rot) in HINTS.items():
        r, c = pos // W, pos % W
        sr, sc = r // 2, c // 2
        slot = slot_names[(r % 2) * 2 + (c % 2)]
        hint_supercells[(sr, sc)] = (slot, pid, rot)

    print("Enumerating initial alphabets...")
    alphabet = {}  # (sr, sc) -> list of blocks
    boundaries = {}  # (sr, sc) -> per-side dict {color_tuple: list of block indices}
    t0 = time.time()
    for sr in range(SW):
        for sc in range(SW):
            pinned = hint_supercells.get((sr, sc))
            if pinned:
                slot, pid, rot = pinned
                blocks = enumerate_blocks_for_supercell(
                    puzzle, sr, sc, pinned_slot=slot, pinned_piece=pid, pinned_rot=rot
                )
            else:
                blocks = enumerate_blocks_for_supercell(puzzle, sr, sc)
            alphabet[(sr, sc)] = blocks
            # Index by boundary
            idx = {0: defaultdict(set), 1: defaultdict(set),
                   2: defaultdict(set), 3: defaultdict(set)}  # side -> tuple -> set of bi
            for bi, b in enumerate(blocks):
                edges = block_outside_edges(b)
                for side in range(4):
                    idx[side][edges[side]].add(bi)
            boundaries[(sr, sc)] = idx
    print(f"  Done in {time.time()-t0:.0f}s. Initial total: {sum(len(b) for b in alphabet.values()):,}")

    # AC-3 propagation: maintain active block-index sets per super-cell
    active = {sc_key: set(range(len(blocks))) for sc_key, blocks in alphabet.items()}

    def side_colors_active(sc_key, side):
        """Set of color tuples currently present on `side` of super-cell sc_key."""
        idx = boundaries[sc_key][side]
        out = set()
        for color, bis in idx.items():
            if bis & active[sc_key]:
                out.add(color)
        return out

    side_dir = [(-1,0), (0,1), (1,0), (0,-1)]
    opposite = [2, 3, 0, 1]

    print("\nAC-3 propagation...")
    for iteration in range(args.max_iters):
        any_change = False
        for (sr, sc) in alphabet:
            if not active[(sr, sc)]: continue
            for side in range(4):
                dr, dc = side_dir[side]
                nr, nc = sr + dr, sc + dc
                if not (0 <= nr < SW and 0 <= nc < SW):
                    continue
                # Our `side` must be in neighbor's opposite-side
                valid_colors = side_colors_active((nr, nc), opposite[side])
                # Filter our active set: keep blocks whose `side` is in valid_colors
                our_idx = boundaries[(sr, sc)][side]
                keep = set()
                for color in valid_colors:
                    keep |= our_idx[color]
                new_active = active[(sr, sc)] & keep
                if new_active != active[(sr, sc)]:
                    any_change = True
                    active[(sr, sc)] = new_active

        total_active = sum(len(s) for s in active.values())
        print(f"  iter {iteration+1}: active total = {total_active:,}"
              f" (any_change={any_change})")
        if not any_change:
            break

    # Final state
    print(f"\nFinal active sizes:")
    sizes = [((sr, sc), len(active[(sr, sc)])) for (sr, sc) in alphabet]
    sizes.sort(key=lambda x: x[1])
    for (sr, sc), n in sizes:
        flag = " HINT" if (sr, sc) in hint_supercells else ""
        print(f"  ({sr},{sc}): {n:>10,}{flag}")
    total = sum(n for _, n in sizes)
    print(f"\nTotal after propagation: {total:,}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({
            "total_after_propagation": total,
            "per_supercell": {f"{sr},{sc}": n for ((sr, sc), n) in sizes},
            "hint_supercells": [list(k) for k in hint_supercells.keys()],
        }, f, indent=2)
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
