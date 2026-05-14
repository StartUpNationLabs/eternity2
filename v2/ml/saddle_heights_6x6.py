"""Vol-35 — find close-Hamming LO pairs at 6×6/5c.

For each pair of LOs within Hamming threshold, report the H and the
score difference. Close-but-different-score pairs suggest a saddle
point between them.
"""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path


def edges_at_pos(placement_list, pos):
    if pos >= len(placement_list):
        return None
    p = placement_list[pos]
    if p is None or not isinstance(p, dict):
        return None
    return (p["piece_id"], p["rotation"])


def hamming(a_pl, b_pl):
    n = min(len(a_pl), len(b_pl))
    return sum(
        1 for k in range(n)
        if edges_at_pos(a_pl, k) != edges_at_pos(b_pl, k)
    )


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "output/vol-35/landscape_6x6_1000"
    files = sorted(glob.glob(f"{root}/lo_*.json"))
    print(f"[load] {len(files)} LOs from {root}")
    if not files:
        return

    boards = []
    for path in files:
        d = json.load(open(path))
        pl = d.get("placement", [])
        score = int(Path(path).stem.split("_s")[-1])
        boards.append((path, score, pl))
    print(f"[load] parsed {len(boards)} boards")

    THRESHOLD = 32
    pairs = []
    print(f"[scan] finding pairs with H ≤ {THRESHOLD} (this scans n^2/2 = {len(boards)*(len(boards)-1)//2} pairs)")
    for i in range(len(boards)):
        for j in range(i + 1, len(boards)):
            h = hamming(boards[i][2], boards[j][2])
            if h <= THRESHOLD:
                pairs.append((i, j, h))
    print(f"[scan] {len(pairs)} pairs with H ≤ {THRESHOLD}")

    if not pairs:
        return

    h_hist = Counter(p[2] for p in pairs)
    print(f"\n=== Pair-Hamming distribution ===")
    for h in sorted(h_hist):
        print(f"  H={h}: {h_hist[h]}")

    print(f"\n=== Top-20 closest pairs (sorted by H ascending) ===")
    pairs_sorted = sorted(pairs, key=lambda p: p[2])
    for i, j, h in pairs_sorted[:20]:
        si, sj = boards[i][1], boards[j][1]
        print(f"  H={h}: scores {si} ↔ {sj} (delta={si - sj})")

    # For comparison: score distribution overall
    scores = [b[1] for b in boards]
    print(f"\n=== Score range: min={min(scores)}, max={max(scores)} ===")


if __name__ == "__main__":
    main()
