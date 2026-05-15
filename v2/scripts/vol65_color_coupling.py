#!/usr/bin/env python3
"""Vol-65 — Color-coupling statistics on known records vs piece supply.

For each piece, the (N, E, S, W) edge colors are a 4-tuple. In the
puzzle's piece supply, certain color-pairs are more common at
specific position-pairs (e.g., color 1 may appear often on the East
side but rarely on the West side — see project_e2_vol65_orientation_asymmetry).

In ASSEMBLED records (459, 469), each matched edge is a (col, col)
self-pair (matching colors). Each MISMATCHED edge is a (col_a, col_b)
pair with col_a ≠ col_b.

Compute:
- Per-color frequency in record matched edges
- Per-color-pair frequency in mismatched edges
- Compare to expected from random pairing

The colors that are OVER-represented in mismatches are the "hard"
colors — pieces with these colors are hard to place compatibly.
"""

import collections
import json
import urllib.parse
from pathlib import Path


def load_grid(path):
    with open(path) as f:
        d = json.load(f)
    url = d.get("bucas_url", d.get("url", ""))
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).fragment)
    if "board_edges" not in qs: return None
    s = qs["board_edges"][0]
    if len(s) != 1024: return None
    g = [[None] * 16 for _ in range(16)]
    for i in range(256):
        r, c = divmod(i, 16)
        seg = s[i*4:(i+1)*4]
        g[r][c] = (ord(seg[0]) - ord('a'), ord(seg[1]) - ord('a'),
                   ord(seg[2]) - ord('a'), ord(seg[3]) - ord('a'))
    return g


def stats(grid):
    """Return matched-color histogram, mismatched-color-pair histogram."""
    matched_colors = collections.Counter()
    mismatched_pairs = collections.Counter()
    for r in range(16):
        for c in range(15):
            a, b = grid[r][c][1], grid[r][c+1][3]
            if a == b:
                matched_colors[a] += 1
            else:
                mismatched_pairs[(min(a,b), max(a,b))] += 1
    for r in range(15):
        for c in range(16):
            a, b = grid[r][c][2], grid[r+1][c][0]
            if a == b:
                matched_colors[a] += 1
            else:
                mismatched_pairs[(min(a,b), max(a,b))] += 1
    return matched_colors, mismatched_pairs


def main():
    paths = [
        ("McGavin-469", "output/community_corpus/groups_172011298_469.json"),
        ("local-459-p06", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"),
        ("vol32-458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"),
        ("vol61-458-s17", "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json"),
        ("vol61-458-s200", "output/vol-61/faithful_sota_20260515T174124/stage3_seed200.json"),
    ]
    for name, p in paths:
        g = load_grid(p)
        if g is None:
            print(f"{name}: skip"); continue
        mc, mp = stats(g)
        print(f"\n=== {name} ===")
        print(f"  Mismatched edges: {sum(mp.values())}")
        print(f"  Mismatched color-pairs (top 10):")
        for (a, b), n in mp.most_common(10):
            print(f"    {a:>2} - {b:>2}: {n}")
        print(f"  Total matched: {sum(mc.values())}")
        # Which colors are over-represented in mismatched edges?
        # Each mismatched edge contributes 1 to each color.
        color_in_mismatch = collections.Counter()
        for (a, b), n in mp.items():
            color_in_mismatch[a] += n
            color_in_mismatch[b] += n
        print(f"  Color participation in mismatches (top 5):")
        for c, n in color_in_mismatch.most_common(5):
            mc_n = mc.get(c, 0)
            print(f"    color {c:>2}: {n} mismatch-uses, {mc_n} matched-uses")


if __name__ == "__main__":
    main()
