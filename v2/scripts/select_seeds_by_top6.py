#!/usr/bin/env python3
"""Select N seeds from a frame_first_e2 stage-1 checkpoint, ranked by
(top-6 universal-mismatch matches DESC, pt_score DESC).

Reads `per_border` entries from the checkpoint JSON (each entry now
includes `bucas_url`), parses each board's quads, counts how many of
the top-6 forbidden edges are MATCHED in that board (= NOT mismatched),
and emits the top-N seeds as a comma-separated string suitable for
`frame_first_e2 --seeds-list`.

Usage:
    python3 select_seeds_by_top6.py CHECKPOINT.json N [FORBIDDEN_JSON]

The third argument defaults to `data/forbidden_top6.json`.

Output: one line with comma-separated seed integers. Diagnostics to stderr.
"""

import argparse
import json
import re
import sys
from pathlib import Path

W = 16
H = 16
BORDER = 0


def parse_bucas(url):
    m = re.search(r'board_edges=([a-z]+)', url)
    if not m:
        return None
    blob = m.group(1)
    quads = [
        tuple(ord(blob[pos * 4 + i]) - ord('a') for i in range(4))
        for pos in range(W * H)
    ]
    return quads


def edge_match_count(quads, edges):
    """Count how many of the given (typ, pos) edges have MATCHING colors
    on both sides (= NOT mismatched, NOT BORDER, valid)."""
    matched = 0
    for typ, pos in edges:
        if typ == 'h':
            pos2 = pos + 1
            side_a, side_b = 1, 3
        else:  # 'v'
            pos2 = pos + W
            side_a, side_b = 2, 0
        if pos2 >= W * H:
            continue
        a = quads[pos][side_a]
        b = quads[pos2][side_b]
        if a == BORDER or b == BORDER:
            # off-board / wildcard — count as "neutral" not as matched
            continue
        if a == b:
            matched += 1
    return matched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checkpoint")
    ap.add_argument("n", type=int)
    ap.add_argument("forbidden_json", nargs='?', default="data/forbidden_top6.json")
    args = ap.parse_args()

    ckpt = json.load(open(args.checkpoint))
    forbidden = json.load(open(args.forbidden_json))
    # forbidden format: [["h", 180], ["h", 91], ...]
    forbidden = [(typ, pos) for typ, pos in forbidden]
    k_max = len(forbidden)

    per_border = ckpt.get("per_border", [])
    print(f"# stage-1 candidates: {len(per_border)}", file=sys.stderr)
    print(f"# top-{k_max} forbidden edges: {forbidden}", file=sys.stderr)

    ranked = []
    for entry in per_border:
        url = entry.get("bucas_url") or ""
        if not url:
            # no board info — skip
            continue
        quads = parse_bucas(url)
        if not quads:
            continue
        n_matched = edge_match_count(quads, forbidden)
        ranked.append({
            "seed": int(entry["seed"]),
            "pt_score": int(entry["pt_score"]),
            "matched_top6": n_matched,
        })

    if not ranked:
        print("# WARN: no boards with bucas_url in checkpoint", file=sys.stderr)
        sys.exit(2)

    # Primary key: matched_top6 DESC. Secondary: pt_score DESC. Tertiary: seed (stability).
    ranked.sort(key=lambda r: (-r["matched_top6"], -r["pt_score"], r["seed"]))

    # Diagnostic table.
    print(f"# rank seed pt_score matched_top6/{k_max}", file=sys.stderr)
    for i, r in enumerate(ranked[:args.n + 5]):
        marker = " <" if i < args.n else ""
        print(f"#  {i+1:3d}  {r['seed']:>11d}  {r['pt_score']}  {r['matched_top6']}/{k_max}{marker}",
              file=sys.stderr)

    seeds = [str(r["seed"]) for r in ranked[:args.n]]
    print(",".join(seeds))


if __name__ == "__main__":
    main()
