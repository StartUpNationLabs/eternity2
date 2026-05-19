#!/usr/bin/env python3
"""V129-T11 — Basin clustering.

For each of the 18 corner-perm basin families, pick the highest-score
representative. Then pairwise compute cell-difference between
representatives. Cluster basins that share many cells.

Output: dendrogram-like text + groupings.
"""

from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "database-400-480"
W = 16
N_CELLS = 256


def load_record(p):
    try: d = json.load(open(p))
    except: return None
    m = d.get("matched")
    pl = d.get("placement", [])
    if not isinstance(m, int): return None
    placement = {int(pp.get("pos", i)): (int(pp["piece_id"]), int(pp["rotation"]))
                 for i, pp in enumerate(pl) if isinstance(pp, dict)}
    if len(placement) != N_CELLS: return None
    return m, placement


def main():
    # Get highest-score per corner perm.
    by_corner: dict = defaultdict(list)
    by_corner_best = {}
    for path in sorted(DB.glob("*.json")):
        r = load_record(path)
        if r is None: continue
        m, pl = r
        if m < 458: continue
        cp = tuple(pl[c][0] for c in (0, 15, 240, 255))
        by_corner[cp].append((m, pl, path.name))
        if cp not in by_corner_best or m > by_corner_best[cp][0]:
            by_corner_best[cp] = (m, pl, path.name)

    print(f"Distinct corner perms (≥458): {len(by_corner_best)}", flush=True)

    # Pairwise diff.
    perms = list(by_corner_best.keys())
    n = len(perms)
    diff_matrix = [[0] * n for _ in range(n)]
    for i, p_i in enumerate(perms):
        for j, p_j in enumerate(perms):
            if i == j: continue
            pl_i = by_corner_best[p_i][1]
            pl_j = by_corner_best[p_j][1]
            d = sum(1 for k in range(N_CELLS) if pl_i[k] != pl_j[k])
            diff_matrix[i][j] = d

    # Print matrix.
    print(f"\nPairwise cell-diff matrix between basin representatives:")
    print(f"{'':>20}", end="")
    for j, p_j in enumerate(perms):
        print(f"{by_corner_best[p_j][0]:>5}", end="")
    print()
    for i, p_i in enumerate(perms):
        score = by_corner_best[p_i][0]
        print(f"{str(p_i):>15} {score:>3}: ", end="")
        for j in range(n):
            if i == j:
                print(f"{'.':>5}", end="")
            else:
                print(f"{diff_matrix[i][j]:>5}", end="")
        print()

    # Find pairs with small diff.
    print(f"\nBasin pairs with diff < 80 (closely related):")
    close_pairs = []
    for i in range(n):
        for j in range(i+1, n):
            d = diff_matrix[i][j]
            if d < 80:
                close_pairs.append((d, perms[i], perms[j],
                                   by_corner_best[perms[i]][0],
                                   by_corner_best[perms[j]][0]))
    close_pairs.sort()
    for d, p_i, p_j, s_i, s_j in close_pairs[:20]:
        print(f"  diff={d:>3}  {p_i}@{s_i} ↔ {p_j}@{s_j}")

    print(f"\n--- Most ISOLATED basins (max min-diff to any other) ---")
    isolation = []
    for i in range(n):
        min_d = min((diff_matrix[i][j] for j in range(n) if j != i), default=N_CELLS)
        isolation.append((min_d, perms[i], by_corner_best[perms[i]][0]))
    isolation.sort(reverse=True)
    for min_d, p, s in isolation[:10]:
        print(f"  {p}@{s}: closest neighbor at diff={min_d}")


if __name__ == "__main__":
    main()
