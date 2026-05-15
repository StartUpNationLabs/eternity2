#!/usr/bin/env python3
"""Vol-76 — Run CAS from each enumerated frame, find best final score.

For each frame in output/vol-76/frame_solution_*.json:
- Use as the starting shell-0
- Run CAS shells 1-7
- Record final score

Hypothesis: some frames give better CAS scores than others.
Best-frame score might be > 433 (our first attempt).
"""

import collections
import csv
import glob
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, 'scripts')
# We need CAS shell-solver
from vol74_cas_full_fixed import solve_shell_fixed, score_full_board, load_pieces, piece_kind


def main():
    pieces = load_pieces()
    interior_pids = [i for i in range(len(pieces)) if piece_kind(pieces[i]) == "interior"]

    frame_files = sorted(glob.glob("output/vol-76/frame_solution_*.json"))
    print(f"Testing {len(frame_files)} frames")
    print(f"{'frame':<35} | {'final score':>11}")

    best = (0, None)
    for fp in frame_files:
        with open(fp) as f: frame_data = json.load(f)
        placement = {item["pos"]: (item["piece_id"], item["rotation"])
                     for item in frame_data["placement"]}
        # Run CAS shells 1-7
        for shell in range(1, 8):
            used = set(p for p, _ in placement.values())
            placement, _ = solve_shell_fixed(shell, placement, pieces, interior_pids, used)
        score = score_full_board(placement, pieces)
        name = Path(fp).stem
        print(f"{name:<35} | {score:>11}")
        if score > best[0]:
            best = (score, fp)

    print(f"\nBest CAS score across {len(frame_files)} frames: {best[0]} (frame={best[1]})")


if __name__ == "__main__":
    main()
