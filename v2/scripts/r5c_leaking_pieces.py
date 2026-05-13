#!/usr/bin/env python3
# R5c — investigate the "leaking pieces" hypothesis.
#
# Hypothesis: 447-class boards have rows 5-6 mismatch because particular
# pieces with the "wrong" edge profile got placed there; in 456-class
# boards, those pieces have been swapped up into rows 0-4.
#
# For each 447 board, list every piece currently in rows 5+ of the
# mismatch region. For each such piece, ask: which row-tier does this
# piece appear in across the 456 boards? If it's consistently in rows
# 0-4 in 456 boards but in 5-6 in 447 boards, that's strong evidence.

import json
import sys
from pathlib import Path

V2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2_ROOT / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("r5", V2_ROOT / "scripts" / "r5_mismatch_homology.py")
r5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r5)

def piece_to_row(board, size):
    # map piece_id -> row (single row, since each piece appears once)
    out = {}
    for pos, entry in enumerate(board):
        if entry is None: continue
        pid, _ = entry
        out[pid] = pos // size
    return out

def board_mismatch_region(board, size, pieces):
    _, mismatched = r5.score_and_classify_edges(board, size, pieces)
    region = set()
    for a, b in mismatched:
        region.add(a); region.add(b)
    return region

def main():
    size, pieces = r5.load_puzzle(r5.PUZZLE_CSV)
    # Two groups of boards
    boards_456 = [
        "output/v17_alns_only/winning5_sa_t1_s1_1778625208.json",
        "output/v17_alns_only/diverse_sa_t1_s1_1778627205.json",
        "output/v17_alns_portfolio/portfolio_winning5_n4_s1_1778624572.json",
        "output/v17_alns_portfolio/portfolio_winning5_n4_s1_1778624147.json",
    ]
    boards_447 = [
        "output/v17_overnight/chunk_0003/alns_best_live.json",
        "output/v17_overnight/chunk_0014/alns_best_live.json",
        "output/v17_overnight/chunk_0002/alns_best_live.json",
    ]

    def load(p):
        path = Path(p).resolve()
        b, _ = r5.load_placement(path, size)
        return b

    boards_456_loaded = [load(p) for p in boards_456]
    boards_447_loaded = [load(p) for p in boards_447]

    # For each 447 board, find pieces in rows 5+ that are in mismatch region.
    print("# Leaking pieces analysis (447-class)")
    print("# For each 447 board, pieces in mismatch region AT rows >= 5,")
    print("# and what row they sit in across the 4 known 456 boards.")
    print()
    for path, b447 in zip(boards_447, boards_447_loaded):
        region = board_mismatch_region(b447, size, pieces)
        leaking = [pos for pos in region if pos // size >= 5]
        leaking_pieces = []
        for pos in leaking:
            pid, _ = b447[pos]
            leaking_pieces.append((pos, pid, pos // size))
        leaking_pieces.sort(key=lambda x: (x[2], x[0]))
        print(f"## {path}")
        print(f"   {len(leaking_pieces)} pieces in rows >= 5 of mismatch region")
        # For each leaking piece, look up its row in each 456 board
        same_row_count = 0
        moved_count = 0
        for pos, pid, row447 in leaking_pieces[:20]:  # cap output
            rows_in_456 = []
            for b456 in boards_456_loaded:
                p2r = piece_to_row(b456, size)
                rows_in_456.append(p2r.get(pid, -1))
            avg_456 = sum(r for r in rows_in_456 if r >= 0) / max(1, sum(1 for r in rows_in_456 if r >= 0))
            same = all(r == row447 for r in rows_in_456)
            moved_to_top = all(r < 5 for r in rows_in_456 if r >= 0)
            if same: same_row_count += 1
            if moved_to_top: moved_count += 1
            print(f"   pos={pos:>3} pid={pid:>3} row447={row447}  rows_in_456={rows_in_456}  avg={avg_456:.1f}  {'(MOVED-UP)' if moved_to_top else '(same)' if same else ''}")
        # Summary
        all_same = 0; all_moved = 0
        for pos, pid, row447 in leaking_pieces:
            rows_in_456 = [piece_to_row(b, size).get(pid, -1) for b in boards_456_loaded]
            if all(r == row447 for r in rows_in_456): all_same += 1
            elif all(r < 5 and r >= 0 for r in rows_in_456): all_moved += 1
        print(f"   summary: {all_same} pieces stay in same row in all 456s; {all_moved} pieces move UP into rows 0-4 in all 456s")
        print()

if __name__ == "__main__":
    main()
