#!/usr/bin/env python3
"""Summarize a NE2 K-sweep across multiple per-K pt_e2 JSONs.

Usage:
    python3 scripts/ne2_analyze.py output/ne2_k_sweep_*.json

Reads the sweep index produced by ne2_k_sweep.sh, then for each K reads
the per-K pt_e2 JSON and tabulates:
  K  raw_best  fmm  pt_seconds  per_replica_final  per_replica_fmm  seed
"""

import json
import re
import sys
from pathlib import Path


W = 16
H = 16
BORDER = 0

# Top-6 edges, hardcoded (matches data/forbidden_top6.json).
TOP6 = [('h',180),('h',91),('v',162),('h',188),('v',183),('v',180)]


def fmm_from_url(url):
    """Compute forbidden-mismatch count over top-6 from bucas URL."""
    m = re.search(r'board_edges=([a-z]+)', url or '')
    if not m:
        return None
    blob = m.group(1)
    quads = [
        tuple(ord(blob[pos * 4 + i]) - ord('a') for i in range(4))
        for pos in range(W * H)
    ]
    fmm = 0
    for typ, pos in TOP6:
        if typ == 'h':
            a, b = quads[pos][1], quads[pos+1][3]
        else:
            a, b = quads[pos][2], quads[pos+W][0]
        if a == BORDER or b == BORDER:
            continue
        if a != b:
            fmm += 1
    return fmm


def main():
    if len(sys.argv) < 2:
        print("usage: ne2_analyze.py sweep.json", file=sys.stderr)
        sys.exit(1)
    sweep = json.load(open(sys.argv[1]))

    print(f"{'K':>5}  {'pt_s':>5}  {'best':>5}  {'fmm':>4}  {'seed':>10}  {'json':>50}")
    print("-" * 90)
    rows = []
    for entry in sweep:
        K = entry["K"]
        pt_s = entry["pt_seconds"]
        seed = entry["seed"]
        jpath = entry["json_path"]
        if not Path(jpath).exists():
            print(f"  K={K}  json missing: {jpath}", file=sys.stderr)
            continue
        j = json.load(open(jpath))
        score = j.get("score", {}).get("matched_edges")
        url = j.get("bucas_url", "")
        fmm = fmm_from_url(url)
        # Also try the per-pt block.
        pt_block = j.get("pt", {})
        best_board_fmm = pt_block.get("best_board_fmm")
        # Prefer the URL-derived fmm (canonical recomputation), fall
        # back to recorded best_board_fmm.
        fmm_final = fmm if fmm is not None else best_board_fmm
        rows.append((K, pt_s, score, fmm_final, seed, jpath))
        print(f"{K:>5}  {pt_s:>5}  {score:>5}  {fmm_final!s:>4}  {seed:>10}  {jpath}")

    print("\n=== highlights ===")
    if not rows:
        print("(no valid rows)")
        return
    best_raw = max(rows, key=lambda r: (r[2] or 0))
    print(f"best raw score: {best_raw[2]} (K={best_raw[0]}, fmm={best_raw[3]})")
    # All-resolved (fmm=0) rows.
    resolved = [r for r in rows if r[3] == 0]
    if resolved:
        best_resolved = max(resolved, key=lambda r: r[2])
        print(f"best fmm=0 (all 6 forbidden RESOLVED): {best_resolved[2]} at K={best_resolved[0]}")
    else:
        print("no run reached fmm=0 (all forbidden edges resolved)")


if __name__ == "__main__":
    main()
