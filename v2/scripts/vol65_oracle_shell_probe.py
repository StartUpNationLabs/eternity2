#!/usr/bin/env python3
"""Vol-65 — Oracle Shell Probe: how much of McGavin 469's structure
is in the OUTER LAYERS vs the interior?

Compute score breakdown of McGavin 469:
- matched edges within perimeter (border-frame)
- matched edges between perimeter and interior (B-I)
- matched edges within shell-1 (cells in rows/cols 1 or 14)
- matched edges within shell-k for k = 1..7
- matched edges in deep interior (cells in rows/cols 7-8)

This tells us how concentrated the "hard-to-find" matches are.

Also: compare to our local-459. Where do the 10-edge advantages live?
"""

import json
import urllib.parse


def load_grid_from_bucas(d):
    url = d.get("bucas_url", d.get("url", ""))
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).fragment)
    if "board_edges" not in qs:
        return None
    s = qs["board_edges"][0]
    if len(s) != 1024:
        return None
    g = [[None] * 16 for _ in range(16)]
    for i in range(256):
        r, c = divmod(i, 16)
        seg = s[i * 4:(i + 1) * 4]
        g[r][c] = (ord(seg[0]) - ord('a'),
                   ord(seg[1]) - ord('a'),
                   ord(seg[2]) - ord('a'),
                   ord(seg[3]) - ord('a'))
    return g


def shell_distance(r, c):
    """Distance from nearest border, in cells. 0 = perimeter, 7-8 = center."""
    return min(r, 15 - r, c, 15 - c)


def main():
    boards = [
        ("McGavin-469", "output/community_corpus/groups_172011298_469.json"),
        ("Local-459", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json"),
        ("vol32-458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"),
    ]

    for name, path in boards:
        with open(path) as f:
            d = json.load(f)
        g = load_grid_from_bucas(d)
        if g is None:
            print(f"{name}: no grid")
            continue

        # Edges classified by max-shell-distance of the two cells they connect
        # Shell-k matches = edges where max-shell(endpoints) = k
        # Equivalently, the "deepest" cell of the edge.
        shell_matched = [0] * 8
        shell_total = [0] * 8
        for r in range(16):
            for c in range(15):
                s1 = shell_distance(r, c)
                s2 = shell_distance(r, c + 1)
                s_max = max(s1, s2)
                shell_total[s_max] += 1
                if g[r][c][1] == g[r][c + 1][3]:
                    shell_matched[s_max] += 1
        for r in range(15):
            for c in range(16):
                s1 = shell_distance(r, c)
                s2 = shell_distance(r + 1, c)
                s_max = max(s1, s2)
                shell_total[s_max] += 1
                if g[r][c][2] == g[r + 1][c][0]:
                    shell_matched[s_max] += 1

        total = sum(shell_total)
        matched = sum(shell_matched)
        print(f"\n=== {name} === total {matched}/{total} = {matched/total*100:.1f}%")
        print(f"  Shell-k (deepest cell of edge is at distance k from frame):")
        for k in range(8):
            if shell_total[k] == 0:
                continue
            pct = shell_matched[k] / shell_total[k] * 100
            print(f"    shell-{k}: {shell_matched[k]:>3} / {shell_total[k]:>3} matched ({pct:.1f}%)")


if __name__ == "__main__":
    main()
