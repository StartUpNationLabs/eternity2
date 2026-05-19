#!/usr/bin/env python3
"""V129-T2 — PALIMPSEST geometric analysis.

For each board cell, count:
- How many cat-A (high-ceiling consensus) pairs involve this cell?
- How many cat-B (consensus trap) pairs involve this cell?

A cell that has many cat-B and 0 cat-A is a "trap cell" — high
priority destroy target. A cell with many cat-A is "structure cell"
— preserve.

Visualize: 16×16 grid with per-cell trap-density.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[1]


def main():
    cons_dirs = sorted((REPO / "output/vol-129").glob("palimpsest_*"))
    cons = json.load(open(cons_dirs[-1] / "consensus.json"))
    print(f"Source: {cons_dirs[-1]}", flush=True)

    n_cells = 256
    W = 16
    HINTS = {34, 45, 135, 210, 221}

    cat_a_count = [0] * n_cells
    cat_b_count = [0] * n_cells

    for p in cons["cat_A_likely_correct"]:
        i, j = p["key"][0], p["key"][1]
        cat_a_count[i] += 1
        cat_a_count[j] += 1
    for p in cons["cat_B_consensus_traps"]:
        i, j = p["key"][0], p["key"][1]
        cat_b_count[i] += 1
        cat_b_count[j] += 1

    print(f"\nPer-cell counts:", flush=True)
    print(f"  Sum cat-A: {sum(cat_a_count)}  Sum cat-B: {sum(cat_b_count)}", flush=True)
    print(f"  Avg cat-A per cell: {sum(cat_a_count)/n_cells:.2f}", flush=True)
    print(f"  Avg cat-B per cell: {sum(cat_b_count)/n_cells:.2f}", flush=True)

    # Highest cat-B (most trap-heavy) cells.
    by_b = sorted(range(n_cells), key=lambda c: -cat_b_count[c])
    print(f"\nTop 20 trap-heavy cells:", flush=True)
    for c in by_b[:20]:
        r, col = c // W, c % W
        hint_mark = " HINT" if c in HINTS else ""
        print(f"  pos={c:>4d} (r={r:>2d}, c={col:>2d})  cat_A={cat_a_count[c]:>3d}  cat_B={cat_b_count[c]:>3d}{hint_mark}", flush=True)

    # Highest cat-A.
    by_a = sorted(range(n_cells), key=lambda c: -cat_a_count[c])
    print(f"\nTop 20 structure cells (cat-A heavy):", flush=True)
    for c in by_a[:20]:
        r, col = c // W, c % W
        hint_mark = " HINT" if c in HINTS else ""
        print(f"  pos={c:>4d} (r={r:>2d}, c={col:>2d})  cat_A={cat_a_count[c]:>3d}  cat_B={cat_b_count[c]:>3d}{hint_mark}", flush=True)

    # Cells with cat-B but ZERO cat-A: pure trap cells.
    pure_trap = [c for c in range(n_cells) if cat_b_count[c] > 0 and cat_a_count[c] == 0]
    print(f"\nPure-trap cells (cat-B > 0, cat-A == 0): {len(pure_trap)}", flush=True)
    if pure_trap:
        print(f"  First 30: {pure_trap[:30]}", flush=True)

    # Visualize 16x16 grid: trap-density per cell.
    print(f"\nCat-B (trap-density) heatmap [16×16]:", flush=True)
    for r in range(W):
        row = []
        for col in range(W):
            c = r * W + col
            v = cat_b_count[c]
            mk = "*" if c in HINTS else " "
            row.append(f"{v:>3d}{mk}")
        print("  " + " ".join(row), flush=True)

    print(f"\nCat-A (structure-density) heatmap [16×16]:", flush=True)
    for r in range(W):
        row = []
        for col in range(W):
            c = r * W + col
            v = cat_a_count[c]
            mk = "*" if c in HINTS else " "
            row.append(f"{v:>3d}{mk}")
        print("  " + " ".join(row), flush=True)


if __name__ == "__main__":
    main()
