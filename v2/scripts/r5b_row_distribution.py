#!/usr/bin/env python3
# R5b — row footprint and "slab thickness" of the mismatch region.
#
# For each board, compute:
#   - distinct rows touched by the mismatch region
#   - max contiguous row-span (e.g., rows 0-3 = span 4)
#   - row-by-row count of mismatch-region cells (slab profile)
#   - the "thickness" metric = (# region cells) / (# distinct rows
#     touched) — higher = thicker slab.
#
# Compare across score tiers to see if thinner slab → higher score.

import json
import sys
from pathlib import Path

V2_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2_ROOT / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("r5", V2_ROOT / "scripts" / "r5_mismatch_homology.py")
r5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r5)

def main():
    size, pieces = r5.load_puzzle(r5.PUZZLE_CSV)
    print(f"# loaded puzzle: size={size}")
    if len(sys.argv) < 2:
        sys.exit("usage: r5b_row_distribution.py <board.json> [...]")
    print()
    print("path | matched | rows_touched | row_span | thickness | profile (rows 0..15)")
    print("-" * 130)
    rows = []
    for arg in sys.argv[1:]:
        p = Path(arg).resolve()
        board, meta = r5.load_placement(p, size)
        if board is None:
            continue
        matched, mismatched = r5.score_and_classify_edges(board, size, pieces)
        region = set()
        for a, b in mismatched:
            region.add(a); region.add(b)
        if not region:
            continue
        row_counts = [0] * size
        for v in region:
            row_counts[v // size] += 1
        rows_touched = sum(1 for c in row_counts if c > 0)
        first = next(i for i, c in enumerate(row_counts) if c > 0)
        last = size - 1 - next(i for i, c in enumerate(reversed(row_counts)) if c > 0)
        row_span = last - first + 1
        thickness = len(region) / rows_touched
        short = str(p.relative_to(V2_ROOT))
        if len(short) > 55: short = "..." + short[-52:]
        profile = " ".join(f"{c:>2}" for c in row_counts)
        print(f"{short} | {matched:>3} | {rows_touched:>2} | {row_span:>2} | {thickness:>5.2f} | {profile}")
        rows.append({"matched": matched, "rows_touched": rows_touched, "row_span": row_span, "thickness": thickness, "region_size": len(region)})

    if rows:
        print()
        print("## by score tier")
        tiers = [(456, 460), (453, 456), (450, 453), (447, 450)]
        for lo, hi in tiers:
            r = [x for x in rows if lo <= x["matched"] < hi]
            if not r: continue
            print(f"  matched ∈ [{lo},{hi}): n={len(r)}  rows_touched_avg={sum(x['rows_touched'] for x in r)/len(r):.2f}  thickness_avg={sum(x['thickness'] for x in r)/len(r):.2f}  region_avg={sum(x['region_size'] for x in r)/len(r):.1f}")

if __name__ == "__main__":
    main()
