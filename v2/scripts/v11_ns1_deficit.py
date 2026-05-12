#!/usr/bin/env python3
"""Quantify NS-1 multiset deficit vs unmatched-edge count across the corpus.

For each board:
- compute A (border-edge-cell inward color multiset)
- compute B (14×14-perimeter outward color multiset)
- multiset_deficit = sum_c |A[c] - B[c]| / 2   (each "wrong" assignment
  shows up as 1 extra in one multiset and 1 less in another)
- unmatched_total = 480 - score (since each unmatched edge is an
  internal join mismatch)
- border_unmatched: how many of the 480-score unmatches are on
  border-interior interfaces (= our deficit predicts this)

Hypothesis: multiset_deficit upper-bounds the number of border-interior
mismatches; that's a fraction of total unmatched (the remainder are
interior-interior mismatches).
"""
from __future__ import annotations

import sys
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]

W = H = 16


def decode_url(url: str):
    m = re.search(r"board_edges=([a-z]+)", url)
    if not m: return None
    blob = m.group(1)
    if len(blob) < W * H * 4: return None
    quads = []
    for pos in range(W * H):
        chunk = blob[pos * 4:pos * 4 + 4]
        quads.append(tuple(ord(c) - ord('a') for c in chunk))
    return quads


def main():
    data = json.load(open(ROOT / "output" / "v11_sp" / "ns1_verification.json"))
    corpus_dir = ROOT / "output" / "community_corpus"

    print(f"{'name':<40s} {'score':>5s} {'480-sc':>6s} {'deficit':>7s} {'2*def':>5s} {'puzzle':<28s}")
    rows = []
    for entry in data["per_board"]:
        name = entry["name"]
        A = entry["A"]; B = entry["B"]
        deficit = sum(abs(A.get(c, 0) - B.get(c, 0)) for c in set(A) | set(B)) // 2
        try:
            meta = json.load(open(corpus_dir / name))
            score = int(meta["interior_matched"])
            puzzle = meta.get("puzzle", "?")
        except Exception:
            continue
        rows.append((score, deficit, name, puzzle))
    rows.sort(key=lambda r: (-r[0], r[1]))
    for score, deficit, name, puzzle in rows[:30]:
        print(f"  {name[:40]:<40s} {score:>5d} {480-score:>6d} {deficit:>7d} {2*deficit:>5d} {puzzle[:28]:<28s}")

    # Scatter for canonical "EternityII"+variants
    print()
    print("=== Canonical EternityII variants only ===")
    can_names = {"Eternity2", "EternityII", "E2nc", "size_16_official"}
    can_rows = [(s, d, n, p) for s, d, n, p in rows if any(k in p for k in can_names)]
    if can_rows:
        for score, deficit, name, puzzle in can_rows[:20]:
            print(f"  {name[:40]:<40s} {score:>5d} {480-score:>6d} {deficit:>7d}  ({puzzle})")


if __name__ == "__main__":
    main()
