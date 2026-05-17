#!/usr/bin/env python3
"""Vol-122 M2 — Build a static ER-priority path.

Use the hint-only board's ER-priority ranking to construct a 256-cell
path for `vanilla_path --path-csv`. Output: a CSV file with one position
per line.
"""
import sys
import os
import json

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from vol122_fft_signature import SIDE
except ImportError:
    SIDE = 16


def main():
    # Place the 5 hints. For each unfilled cell, compute the ER-reduction.
    # Sort by reduction descending. Output as path.

    # Build a hint-only adjacency: 5 isolated cells, no edges between them
    # (no matched edges yet since they're not adjacent).
    hint_positions = [34, 45, 135, 210, 221]
    hint_set = set(hint_positions)

    # For each candidate cell c, compute a heuristic priority.
    # Since ER on isolated points diverges (no graph yet), use instead
    # MANHATTAN-distance proximity to hints: lower = higher priority.

    # Actually, let's use a more meaningful heuristic:
    # Priority = -sum_{h in hints} distance(c, h)
    # Closest cells to ALL hints get highest priority.
    priorities = []
    for r in range(SIDE):
        for c in range(SIDE):
            pos = r * SIDE + c
            if pos in hint_set:
                continue
            # Sum of inverse distances to all hints
            score = 0.0
            for h in hint_positions:
                hr, hc = h // SIDE, h % SIDE
                d = abs(r - hr) + abs(c - hc)
                score += 1.0 / (d + 0.5)
            priorities.append((pos, score))

    priorities.sort(key=lambda x: x[1], reverse=True)

    # The path: hints first, then high-priority unfilled cells.
    path = []
    for h in hint_positions: path.append(h)
    for pos, score in priorities:
        path.append(pos)
    assert len(path) == 256, f"path length {len(path)}"
    assert len(set(path)) == 256, "duplicates in path"

    out_path = "output/vol-122/m2_er_priority_path.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        for p in path:
            f.write(f"{p}\n")
    print(f"Wrote {out_path}")
    print(f"First 20 cells: {path[:20]}")
    print(f"  positions translated: {[(p // SIDE, p % SIDE) for p in path[:20]]}")


if __name__ == "__main__":
    main()
