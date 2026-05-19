#!/usr/bin/env python3
"""V127-T4 — CONCRETION step 4: 2-step border-ring lookahead.

Even though no piece has a unique successor (out-degree 9-12), some
2-piece paths might be uniquely extendable. Build a 2-step adjacency
graph: count (P, Q, R) triples where P→Q→R is a viable top-row triple.

For each (P, Q), how many R extensions exist? If ≤ some threshold,
we have forced 3-piece chains.

A 60-piece ring + 4 corners means the top row has 14 edge pieces
between 2 corners. So we need chains of length ~12 between corner-edge
pieces.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

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


def rotate_piece(piece, r):
    N, E, S, W = piece
    return [(N, E, S, W), (E, S, W, N), (S, W, N, E), (W, N, E, S)][r]


def main():
    csv_path = REPO.parent / "data/puzzles/size_16_official_eternity.csv"
    size, pieces = load_puzzle_csv(csv_path)

    edge_ids = [pid for pid, p in enumerate(pieces) if sum(1 for s in p if s == 0) == 1]
    # canonical top-row rotation: N=0.
    top_orient = {}
    for pid in edge_ids:
        for r in range(4):
            p_r = rotate_piece(pieces[pid], r)
            if p_r[0] == 0 and p_r[2] != 0:
                # Found N=0, S≠0 → record E and W (the ring-facing colors).
                top_orient[pid] = (r, p_r[1], p_r[3])  # (rot, E, W)
                break

    # Successors: q follows p iff p.E == q.W.
    succ = defaultdict(set)
    for p in edge_ids:
        _, e, _ = top_orient[p]
        for q in edge_ids:
            if q == p: continue
            _, _, w = top_orient[q]
            if e == w:
                succ[p].add(q)

    # 2-step successors with COUNTS
    succ2 = defaultdict(set)  # (p) → set of (q, r) such that p→q→r
    for p in edge_ids:
        for q in succ[p]:
            for r in succ[q]:
                if r == p or r == q: continue
                succ2[p].add((q, r))

    # For each starting piece p, how many 2-step extensions?
    n_extensions = Counter(len(extensions) for p, extensions in succ2.items())
    print(f"\n2-step extension count distribution:", flush=True)
    for cnt in sorted(n_extensions.keys()):
        print(f"  {cnt} 2-step extensions: {n_extensions[cnt]} starting pieces", flush=True)

    # 3-step
    succ3_count = defaultdict(int)
    sample_pieces = sorted(succ2.keys())[:5]
    print(f"\n3-step extensions for first few pieces:", flush=True)
    for p in sample_pieces:
        n3 = 0
        for (q, r) in succ2[p]:
            for s in succ[r]:
                if s in (p, q, r): continue
                n3 += 1
        succ3_count[p] = n3
        print(f"  p={p} 3-step count: {n3}", flush=True)

    # Try a deeper enumeration: how many 14-piece top rows exist?
    # The top row uses 14 edge pieces between 2 corners. The first and last
    # piece must match the corner's interior-facing side colors.
    # We're going to count without corner constraint for now: how many
    # length-14 simple paths in the directed succ graph?
    # Use DFS with depth limit.

    # Path counts: don't enumerate, count via DP over (last_piece, used_set).
    # But the used_set is 2^56 → too big. Use a relaxation: count by length
    # only (allowing repeats), then divide by overcounting estimate.
    # Easier metric: average branching factor.
    branching = []
    for p in edge_ids:
        for q in succ[p]:
            branching.append(len(succ[q]))
    import statistics
    print(f"\nBranching factor stats: min={min(branching)} median={statistics.median(branching)} "
          f"mean={statistics.mean(branching):.2f} max={max(branching)}", flush=True)

    # Expected number of length-14 paths (the top row) without repeat-pruning:
    # ~ avg_outdeg^14. With repeat-pruning the real number is smaller.
    print(f"  with avg_outdeg={statistics.mean(branching):.2f}, naive 14-step ~ {statistics.mean(branching)**14:.2e}", flush=True)


if __name__ == "__main__":
    main()
