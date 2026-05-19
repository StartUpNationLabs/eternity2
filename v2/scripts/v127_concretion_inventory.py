#!/usr/bin/env python3
"""V127-T1 — CONCRETION step 1: canonical color inventory.

For canonical E2 (16×16, 22 interior colors + border=0), enumerate:
  - For each color C: list of (piece, side) occurrences where that side's
    color in the piece's CANONICAL orientation is C.
  - Per-piece edge color profile.
  - Distribution of colors across pieces.

Output: JSON with color → list of (piece_id, side) tuples.
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from collections import Counter, defaultdict

REPO = Path(__file__).resolve().parents[1]


def load_puzzle_csv(csv_path):
    BORDER_RAW = 65535
    pieces = []
    with open(csv_path) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            sides = []
            for s in parts[:4]:
                v = int(s.strip(), 2)
                sides.append(0 if v == BORDER_RAW else v)
            pieces.append(tuple(sides))
    return size, pieces


def main():
    csv_path = REPO.parent / "data/puzzles/size_16_official_eternity.csv"
    size, pieces = load_puzzle_csv(csv_path)
    print(f"Puzzle: {csv_path.name}  pieces={len(pieces)}", flush=True)

    # Side index: 0=N, 1=E, 2=S, 3=W.
    SIDE_NAMES = ["N", "E", "S", "W"]

    color_to_occs = defaultdict(list)  # color → list of (piece_id, side)
    for pid, (N, E, S, W) in enumerate(pieces):
        for side_idx, c in enumerate([N, E, S, W]):
            color_to_occs[c].append((pid, side_idx))

    print(f"\nColors observed: {sorted(color_to_occs.keys())}", flush=True)
    print(f"\n{'color':>6} {'k':>5} {'rarity':>10}", flush=True)
    for c in sorted(color_to_occs.keys()):
        k = len(color_to_occs[c])
        rarity = "BORDER" if c == 0 else ("rare" if k <= 24 else "medium" if k <= 48 else "common")
        print(f"{c:>6d} {k:>5d} {rarity:>10}", flush=True)

    # Categorize pieces by edge-color profile.
    print(f"\nPiece-type taxonomy:", flush=True)
    n_corners = 0
    n_borders = 0
    n_interior = 0
    rare_set = {c for c in color_to_occs if c != 0 and len(color_to_occs[c]) <= 24}
    interior_rare_count = []
    for pid, (N, E, S, W) in enumerate(pieces):
        sides = [N, E, S, W]
        n_zero = sum(1 for s in sides if s == 0)
        if n_zero == 2:
            n_corners += 1
        elif n_zero == 1:
            n_borders += 1
        else:
            n_interior += 1
            n_rare_sides = sum(1 for s in sides if s in rare_set)
            interior_rare_count.append((pid, n_rare_sides, sides))
    print(f"  corners: {n_corners}", flush=True)
    print(f"  borders: {n_borders}", flush=True)
    print(f"  interior: {n_interior}", flush=True)

    # Interior pieces by rare-side count.
    rare_count_distrib = Counter(n_rare for _, n_rare, _ in interior_rare_count)
    print(f"\nInterior pieces by rare-side count:", flush=True)
    for k in sorted(rare_count_distrib.keys()):
        print(f"  {k} rare sides: {rare_count_distrib[k]} pieces", flush=True)

    # The "4-rare" interior pieces — most constrained.
    quad_rare = [p for p, n, _ in interior_rare_count if n == 4]
    print(f"\n4-rare interior pieces ({len(quad_rare)}):", flush=True)
    for pid in quad_rare:
        print(f"  pid={pid} sides={pieces[pid]}", flush=True)

    # Save.
    out_dir = REPO / "output/vol-127"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "color_inventory.json"
    with open(out_path, "w") as f:
        json.dump({
            "n_pieces": len(pieces),
            "color_to_occs": {str(c): [list(t) for t in occs] for c, occs in color_to_occs.items()},
            "rare_colors": sorted(rare_set),
            "stats": {
                "n_corners": n_corners,
                "n_borders": n_borders,
                "n_interior": n_interior,
                "quad_rare_count": len(quad_rare),
                "interior_by_rare_sides": dict(rare_count_distrib),
            },
        }, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
