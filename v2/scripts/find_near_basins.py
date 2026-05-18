#!/usr/bin/env python3
"""Find near-basin pairs in database-400-480.

For each pair of boards (A, B) in DB:
- Compute cell-difference: |{pos : A[pos] != B[pos]}|
- Sort by smallest cell-diff first

Output: top 50 near-pairs with their bucas URLs + scores.
Near pairs (diff < 50 cells) are candidates for bridge attacks.
"""

import json
from pathlib import Path
from itertools import combinations

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
DB = REPO / "database-400-480"
OUT = REPO / "output" / "vol-125" / "near_basins"
OUT.mkdir(parents=True, exist_ok=True)


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    pl = d.get("placement", [])
    return {p["pos"]: (p["piece_id"], p["rotation"]) for p in pl}, d.get("matched", 0)


def diff_count(a, b):
    """Cell-difference: cells where (piece_id, rotation) differ."""
    diff = 0
    all_pos = set(a.keys()) | set(b.keys())
    for pos in all_pos:
        if a.get(pos) != b.get(pos):
            diff += 1
    return diff


def main():
    print(f"Loading boards from {DB}...", flush=True)
    boards = []
    for f in sorted(DB.glob("*.json")):
        if f.name == "README.md": continue
        try:
            placements, score = load_board(f)
            if len(placements) == 256:  # complete only
                boards.append((f.name, score, placements))
        except Exception:
            continue
    print(f"  loaded {len(boards)} complete boards", flush=True)

    # Filter to high-score boards for tractability (top ~200).
    high = sorted(boards, key=lambda b: -b[1])[:200]
    print(f"  using top {len(high)} by score for pairwise diff", flush=True)

    # Pairwise diffs.
    pairs = []
    n = len(high)
    for i in range(n):
        if i % 50 == 0:
            print(f"  i={i}/{n}", flush=True)
        for j in range(i + 1, n):
            name_a, sa, ba = high[i]
            name_b, sb, bb = high[j]
            d = diff_count(ba, bb)
            if d < 100:  # near-basin filter
                pairs.append((d, name_a, sa, name_b, sb))

    pairs.sort()
    print(f"\nFound {len(pairs)} near-pairs (diff < 100)", flush=True)
    print(f"\nTop 30 nearest pairs:", flush=True)
    for d, na, sa, nb, sb in pairs[:30]:
        print(f"  diff={d:3d}  {na[:35]:>36}({sa})  ↔  {nb[:35]:>36}({sb})", flush=True)

    out_path = OUT / "near_pairs.json"
    out_data = [
        {"diff": d, "name_a": na, "score_a": sa, "name_b": nb, "score_b": sb}
        for d, na, sa, nb, sb in pairs[:200]
    ]
    out_path.write_text(json.dumps(out_data, indent=2))
    print(f"\nSaved top 200 to {out_path}")


if __name__ == "__main__":
    main()
