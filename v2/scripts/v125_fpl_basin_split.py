#!/usr/bin/env python3
"""V125-T34b — FPL with basin separation.

Refinement of v125_fpl_analysis.py:
- Bucket records by *corner permutation* (4-tuple of piece IDs at corners 0/15/240/255).
- This separates our 459-461 basin (perm A) from McGavin's 469 basin (perm B).
- Compute log-odds against MID/LOW BUT ONLY within the same basin family.

The key question: are there pairs invariant across the McGavin
462-469 boards that are ABSENT in our 459-461 boards? Those pairs
are the "McGavin signature" — pinning them might transport our
search to McGavin-class scores.
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict, Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "database-400-480"
OUT_DIR = REPO / "output" / "vol-125" / f"fpl_basin_{time.strftime('%Y%m%dT%H%M%S')}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W = 16
N_CELLS = 256
CORNER_POS = (0, 15, 240, 255)


def adjacent_pairs():
    for r in range(W):
        for c in range(W):
            i = r * W + c
            if c < W - 1:
                yield (i, i + 1, 'E')
            if r < W - 1:
                yield (i, i + W, 'S')


def load_record(path: Path):
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        return None
    matched = d.get("matched")
    pl = d.get("placement", [])
    if not isinstance(matched, int) or not isinstance(pl, list):
        return None
    placement = {}
    for idx, p in enumerate(pl):
        if not isinstance(p, dict):
            continue
        pos = p.get("pos", idx)
        if "piece_id" in p and "rotation" in p:
            placement[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    if len(placement) != N_CELLS:
        return None
    return matched, placement, path.name


def main():
    print(f"OUT_DIR={OUT_DIR}", flush=True)
    records = []
    for path in sorted(DB.glob("*.json")):
        r = load_record(path)
        if r is None:
            continue
        records.append(r)

    # Bucket by corner perm.
    by_corner: dict[tuple, list] = defaultdict(list)
    for matched, placement, name in records:
        corner_pids = tuple(placement[c][0] for c in CORNER_POS)
        by_corner[corner_pids].append((matched, placement, name))

    print(f"\nCorner permutation distribution (top 10):", flush=True)
    sorted_corners = sorted(by_corner.items(), key=lambda x: -len(x[1]))
    for perm, recs in sorted_corners[:10]:
        scores = sorted([m for m, _, _ in recs], reverse=True)
        print(f"  corner_pids={perm}: {len(recs)} records, top-5 scores: {scores[:5]}", flush=True)

    # Top-scoring corner perm (most likely McGavin-class).
    # Identify the perm holding the 469 boards.
    mcgavin_perms = set()
    our_perms = set()
    for perm, recs in by_corner.items():
        max_score = max(m for m, _, _ in recs)
        if max_score >= 462:
            mcgavin_perms.add(perm)
        if max_score == 461:
            our_perms.add(perm)
    print(f"\nMcGavin-class perms (max ≥ 462): {mcgavin_perms}")
    print(f"Our 461 perms (max == 461):       {our_perms}")

    # FPL across full DB but flag which basin each pair-tuple is most associated with.
    pair_geometry = list(adjacent_pairs())

    # For each pair-tuple at a position, track:
    #   set of basins (corner_perm tuples) in which the pair appears
    #   per-basin max score
    pair_basin_max: dict[tuple, dict] = defaultdict(lambda: defaultdict(int))
    pair_count: dict[tuple, int] = defaultdict(int)

    for matched, placement, name in records:
        corner = tuple(placement[c][0] for c in CORNER_POS)
        for (i, j, d) in pair_geometry:
            pi, ri = placement[i]
            pj, rj = placement[j]
            key = (i, j, d, pi, ri, pj, rj)
            pair_count[key] += 1
            if matched > pair_basin_max[key][corner]:
                pair_basin_max[key][corner] = matched

    # Find pairs that ONLY appear in McGavin-class basins.
    mcgavin_only_pairs = []
    for key, basin_map in pair_basin_max.items():
        in_mcgavin = any(b in mcgavin_perms for b in basin_map)
        in_other = any(b not in mcgavin_perms for b in basin_map)
        if in_mcgavin and not in_other:
            # Pair signature of McGavin basin alone.
            max_in_mcgavin = max(v for b, v in basin_map.items() if b in mcgavin_perms)
            n_records = pair_count[key]
            mcgavin_only_pairs.append((key, n_records, max_in_mcgavin))

    mcgavin_only_pairs.sort(key=lambda x: (-x[2], -x[1]))
    print(f"\nMcGavin-only pair-tuples: {len(mcgavin_only_pairs)}", flush=True)
    print(f"Top 20:", flush=True)
    print(f"{'i':>4} {'j':>4} {'d':>2} {'pi':>4} {'ri':>3} {'pj':>4} {'rj':>3} {'n':>3} {'max':>4}", flush=True)
    for key, n, mx in mcgavin_only_pairs[:20]:
        i, j, d, pi, ri, pj, rj = key
        print(f"{i:>4} {j:>4} {d:>2} {pi:>4} {ri:>3} {pj:>4} {rj:>3} {n:>3} {mx:>4}", flush=True)

    out = {
        "n_records": len(records),
        "mcgavin_perms": [list(p) for p in mcgavin_perms],
        "our_perms": [list(p) for p in our_perms],
        "n_mcgavin_only_pairs": len(mcgavin_only_pairs),
        "top_pairs": [
            {"i": k[0], "j": k[1], "dir": k[2], "pi": k[3], "ri": k[4],
             "pj": k[5], "rj": k[6], "n": n, "max_score": mx}
            for k, n, mx in mcgavin_only_pairs[:500]
        ],
    }
    out_path = OUT_DIR / "fpl_mcgavin_pairs.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
