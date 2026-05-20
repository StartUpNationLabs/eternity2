#!/usr/bin/env python3
"""V188-T1 — compute the piece-permutation π between two boards.

At each position p, board_a places piece a_p, board_b places piece b_p.
The piece-permutation π is defined by: π(a_p) = b_p at every p.

For π to be a valid PERMUTATION, the mapping must be consistent across
positions (each piece a_p maps to exactly one piece b_p). If a piece
appears at multiple positions in a_p (impossible if both boards are
valid), or if different positions yield conflicting mappings, π isn't
well-defined globally.

In practice: for two complete valid E2 placements, every piece appears
exactly once in each board. So π is well-defined as
π(piece_id) = b_p where p is the (unique) position of piece_id in a.

Note: π acts on PIECE-IDs, not positions. To "apply" π to a board, we
relabel pieces at each position: new[p] = π(a[p]).

For our use: a = V181 460, b = McGavin 469. After computing π,
decompose into cycles. Smaller cycles = more local transport.
"""
import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border, score_full

REPO = Path(__file__).resolve().parents[2]


def load_placement(path):
    board = json.load(open(path))
    pl = [None] * 256
    for ent in board['placement']:
        if ent is not None:
            pl[ent['pos']] = (ent['piece_id'], ent['rotation'])
    return pl, board.get('matched', 0)


def piece_to_pos(pl):
    """Returns dict {piece_id: (position, rotation)} for full placement."""
    m = {}
    for pos in range(256):
        if pl[pos] is not None:
            pid, rot = pl[pos]
            assert pid not in m, f"piece {pid} appears at pos {m[pid][0]} AND {pos}"
            m[pid] = (pos, rot)
    return m


def cycle_decomposition(perm):
    """perm: dict {key: value}. Returns list of cycles, each as list of keys."""
    cycles = []
    visited = set()
    for start in sorted(perm.keys()):
        if start in visited: continue
        cycle = [start]
        x = perm[start]
        while x != start:
            cycle.append(x)
            visited.add(x)
            if x not in perm:
                # Open chain, not a cycle.
                cycle = None
                break
            x = perm[x]
        if cycle is not None:
            visited.add(start)
            cycles.append(cycle)
    return cycles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--board-a', default='output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json')
    ap.add_argument('--board-b', default='database-400-480/469_mcgavin_469_6c9a2448.json')
    args = ap.parse_args()

    pieces = load_pieces()
    pl_a, score_a = load_placement(REPO / args.board_a)
    pl_b, score_b = load_placement(REPO / args.board_b)
    print(f"Board A: {args.board_a}  score={score_a}")
    print(f"Board B: {args.board_b}  score={score_b}")

    # Compute corner perms.
    def corner_perm(pl):
        return tuple(pl[p][0] for p in [0, 15, 240, 255])
    cp_a = corner_perm(pl_a)
    cp_b = corner_perm(pl_b)
    print(f"Board A corner perm: {cp_a}")
    print(f"Board B corner perm: {cp_b}")

    # Compute π: π(piece at pos p in A) = piece at pos p in B.
    pi = {}
    for pos in range(256):
        a_pid = pl_a[pos][0]
        b_pid = pl_b[pos][0]
        if a_pid in pi:
            if pi[a_pid] != b_pid:
                print(f"  CONFLICT: piece {a_pid} maps to {pi[a_pid]} AND {b_pid}")
        else:
            pi[a_pid] = b_pid

    # Sanity: π must be a bijection.
    img = set(pi.values())
    print(f"\nπ domain size: {len(pi)} (= 256?)")
    print(f"π image size: {len(img)} (= 256?)")
    if len(pi) != 256 or len(img) != 256:
        print("WARN: π is not a full bijection on 256 pieces")

    # Find fixed points and cycle decomposition.
    fixed = [k for k, v in pi.items() if k == v]
    print(f"\nFixed points (pieces in same position via π): {len(fixed)}")
    print(f"  Sample: {fixed[:20]}")

    cycles = cycle_decomposition(pi)
    cycle_lens = sorted(len(c) for c in cycles)
    print(f"\nCycle lengths (count): {len(cycles)} cycles total")
    from collections import Counter
    print(f"  Distribution: {Counter(cycle_lens)}")

    # Now: which cycles are confined to BOTTOM ROWS (11-15) in board A?
    bottom_positions = set(r * 16 + c for r in range(11, 16) for c in range(16))
    bottom_pieces_a = set(pl_a[p][0] for p in bottom_positions)
    # A cycle is "bottom-confined" if ALL its pieces are in bottom_pieces_a.
    bottom_confined = []
    for c in cycles:
        if all(p in bottom_pieces_a for p in c):
            bottom_confined.append(c)
    print(f"\nBottom-confined cycles (rows 11-15 of board A): {len(bottom_confined)}")
    for c in bottom_confined[:10]:
        print(f"  cycle of length {len(c)}: {c[:8]}...")

    # Similarly bottom-confined in BOARD B image side.
    bottom_pieces_b = set(pl_b[p][0] for p in bottom_positions)
    # A cycle C in A is bottom-AND-bottom if pi(C) ⊆ bottom_pieces_b.
    # Means: pieces in A's bottom map to pieces also in B's bottom.
    fully_bottom = []
    for c in cycles:
        if all(p in bottom_pieces_a for p in c) and all(pi[p] in bottom_pieces_b for p in c):
            fully_bottom.append(c)
    print(f"\nDoubly-bottom-confined cycles (rows 11-15 in both A and B): {len(fully_bottom)}")
    for c in fully_bottom[:10]:
        print(f"  cycle of length {len(c)}: {c[:8]}")

    return pi, cycles, bottom_positions, pl_a, pl_b


if __name__ == '__main__':
    main()
