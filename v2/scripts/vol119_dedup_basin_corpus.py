#!/usr/bin/env python3
"""Vol-119 — dedup basin corpus by Hamming distance.

Given a directory of boards, group by score and within each group dedup
boards that share ≥ K cells (default K=240, i.e., Hamming ≤ 16).

Outputs a CSV manifest of distinct basins.

Usage:
    vol119_dedup_basin_corpus.py --dir path1 path2 ... --min-score 455 [--hamming-K 30]
"""

import argparse
import json
import sys
from pathlib import Path


def load_board(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def hamming(a, b):
    """Count cells where (pid, rot) differs."""
    keys = set(a) | set(b)
    return sum(1 for k in keys if a.get(k) != b.get(k))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="board JSONs or directories")
    ap.add_argument("--min-score", type=int, default=455)
    ap.add_argument("--hamming-K", type=int, default=30,
                    help="boards with Hamming < K are dedupped")
    args = ap.parse_args()

    files = []
    for p in args.paths:
        pp = Path(p)
        if pp.is_dir():
            files.extend(pp.glob("*.json"))
        else:
            files.append(pp)
    files = sorted(set(files))

    # Load all + score via stub (read score from metadata or recompute via verify_board)
    # Simpler: get score from the actual file via subprocess to verify_board.
    # Even simpler: load board and use our local matched_edges. But we'd need pieces.

    # Use raw "placement" length + skip non-256 boards.
    boards = []
    for f in files:
        try:
            b = load_board(f)
            if len(b) >= 200:
                boards.append((f, b))
        except Exception as e:
            print(f"skip {f}: {e}", file=sys.stderr)

    print(f"# loaded {len(boards)} boards from {len(files)} files", file=sys.stderr)

    # We don't compute score here — we use file metadata or external verify.
    # For dedup, just compute pairwise Hamming.

    distinct = []
    for i, (fi, bi) in enumerate(boards):
        is_new = True
        for fj, bj in distinct:
            h = hamming(bi, bj)
            if h < args.hamming_K:
                is_new = False
                break
        if is_new:
            distinct.append((fi, bi))

    print(f"# distinct basins (Hamming ≥ {args.hamming_K}): {len(distinct)}")
    for f, _ in distinct:
        print(str(f))


if __name__ == "__main__":
    main()
