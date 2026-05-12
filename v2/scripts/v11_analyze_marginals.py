#!/usr/bin/env python3
"""Analyze structure of BP marginals.

Questions:
1. Per-cell entropy spatial heatmap — where does BP carry the most info?
2. Color marginals per side — which colors dominate where?
3. Piece-occupancy histogram — which pieces are most/least claimed?
4. Pairwise correlation: are polarized cells clustered or dispersed?
5. Hint propagation distance — how far does each hint's information reach?

Findings get written to output/v11_sp/marginals_analysis.{json,txt}.
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from collections import defaultdict

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load
from v11_factor_graph import cell_class, SIZE, N

MARGINALS = ROOT / "output" / "v11_sp" / "bp_marginals.json"


def main():
    with MARGINALS.open() as f:
        data = json.load(f)
    puzzle = load()
    pieces = puzzle["pieces"]
    hint_positions = {pos for pos, _, _ in puzzle["hints"]}

    H = np.zeros(N)
    n_states = np.zeros(N, dtype=np.int32)
    top1_marg = np.zeros(N)  # marginal of top state
    top1_pid = -np.ones(N, dtype=np.int32)
    top3_mass = np.zeros(N)
    # Piece occupancy: pid -> sum of marginals across cells
    piece_occ = np.zeros(256)
    # Color marginal per (pos, side, color)
    color_marg = np.zeros((N, 4, 23))
    # For each cell, the marginal of each piece-id (sum over rotations)
    piece_marg_at_cell = np.zeros((N, 256))

    for cell in data["marginals"]:
        pos = cell["pos"]
        H[pos] = cell["entropy"]
        n_states[pos] = cell["n_states"]
        states = cell["states"]
        if states:
            top1_marg[pos] = states[0]["marginal"]
            top1_pid[pos] = states[0]["piece_id"]
            top3_mass[pos] = sum(s["marginal"] for s in states[:3])
        for s in states:
            pid = s["piece_id"]; rot = s["rotation"]; p = s["marginal"]
            piece_occ[pid] += p
            piece_marg_at_cell[pos, pid] += p
            # Compute color exposed on each side for this state
            from v11_load_e2 import rotate_edges
            edges = rotate_edges(pieces[pid], rot)
            for side in range(4):
                color_marg[pos, side, int(edges[side])] += p

    # Entropy heatmap (text)
    print("=== Per-cell entropy heatmap (text) ===")
    print("dots scale: . < 1 .. < 2 / < 3 + < 4 - < 5 = < 5.5 # < 6 @ < 6.5 * else")
    sym = ".../+-=#@*"
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            pos = y * SIZE + x
            if pos in hint_positions:
                row.append("H")
                continue
            h = H[pos]
            if h < 1: row.append(".")
            elif h < 2: row.append("/")
            elif h < 3: row.append("+")
            elif h < 4: row.append("-")
            elif h < 5: row.append("=")
            elif h < 5.5: row.append("#")
            elif h < 6: row.append("@")
            else: row.append("*")
        print("  " + "".join(row))
    print()

    # Top-marginal heatmap: how concentrated is the top state?
    print("=== top-1 marginal heatmap ===")
    print("0:[0,0.05) 1:[0.05,0.10) 2:[0.10,0.20) 3:[0.20,0.40) 4:[0.40,0.70) 5:[0.70,1.0]")
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            pos = y * SIZE + x
            if pos in hint_positions:
                row.append("H")
                continue
            m = top1_marg[pos]
            if m < 0.05: row.append("0")
            elif m < 0.10: row.append("1")
            elif m < 0.20: row.append("2")
            elif m < 0.40: row.append("3")
            elif m < 0.70: row.append("4")
            else: row.append("5")
        print("  " + "".join(row))
    print()

    # Piece occupancy stats
    hint_pids = {pid for _, pid, _ in puzzle["hints"]}
    non_hint = np.array([piece_occ[p] for p in range(256) if p not in hint_pids])
    print("=== Piece occupancy stats ===")
    print(f"  hint pieces: " + " ".join(f"{pid}={piece_occ[pid]:.2f}" for pid in sorted(hint_pids)))
    print(f"  non-hint:   sum={non_hint.sum():.2f} (max 251) min={non_hint.min():.3f} "
          f"max={non_hint.max():.3f} mean={non_hint.mean():.3f}")

    # Most-overclaimed pieces
    top10_over = np.argsort(-piece_occ)[:10]
    print(f"  top-10 by occupancy: " + ", ".join(f"{pid}:{piece_occ[pid]:.3f}" for pid in top10_over))
    # Least-occupied (most "leftover" mass)
    bot10 = np.argsort(piece_occ)[:10]
    print(f"  bottom-10 by occupancy: " + ", ".join(f"{pid}:{piece_occ[pid]:.3f}" for pid in bot10))
    print()

    # Hint "reach": for each hint, count cells where the hinted piece-id
    # has positive marginal. Tests how much information each hint provides.
    print("=== Hint reach (cells with piece_marg > 0.01 for the hint's pid) ===")
    for hpos, hpid, hrot in puzzle["hints"]:
        reach = (piece_marg_at_cell[:, hpid] > 0.01).sum()
        # Subtract 1 (the hint cell itself)
        print(f"  hint pid={hpid} at pos=({hpos%SIZE},{hpos//SIZE}): "
              f"cells_with_residual_marginal={reach - 1}  total_occupancy={piece_occ[hpid]:.3f}")
    print()

    # Spatial clustering of polarization: are low-entropy cells adjacent?
    # Count adjacent pairs both in lowest-entropy quartile vs random expectation
    threshold = np.quantile(H[~np.isin(np.arange(N), list(hint_positions))], 0.25)
    print(f"=== Spatial clustering test (low-H threshold = 25th percentile = {threshold:.3f}) ===")
    low_H = H <= threshold
    low_count = int(low_H.sum())
    adj_count = 0
    adj_both_low = 0
    for pos in range(N):
        x, y = pos % SIZE, pos // SIZE
        for (nx, ny) in [(x+1, y), (x, y+1)]:
            if 0 <= nx < SIZE and 0 <= ny < SIZE:
                npos = ny * SIZE + nx
                adj_count += 1
                if low_H[pos] and low_H[npos]:
                    adj_both_low += 1
    expected = adj_count * (low_count / N) ** 2
    print(f"  total adjacent pairs: {adj_count}")
    print(f"  pairs where BOTH low-H: {adj_both_low}")
    print(f"  expected if random:    {expected:.1f}")
    enrichment = adj_both_low / max(expected, 0.001)
    print(f"  enrichment factor:     {enrichment:.2f}× (>1 = clustered)")
    print()

    # Color marginal at corners
    print("=== Color marginals at corner cells (inward sides) ===")
    corners = [(0, 0, "TL", (2, 1)), (SIZE - 1, 0, "TR", (2, 3)),
               (0, SIZE - 1, "BL", (0, 1)), (SIZE - 1, SIZE - 1, "BR", (0, 3))]
    for cx, cy, name, inward_sides in corners:
        pos = cy * SIZE + cx
        print(f"  {name} corner ({cx},{cy}):")
        for side in inward_sides:
            top_c = np.argsort(-color_marg[pos, side])[:5]
            sname = "TRBL"[side]
            print(f"    side {sname}: " + ", ".join(f"c{c}:{color_marg[pos, side, c]:.3f}" for c in top_c))
    print()

    # Save summary
    summary = {
        "schema_version": 1,
        "stats": {
            "mean_H_all": float(H.mean()),
            "mean_top1": float(top1_marg.mean()),
            "mean_top3_mass": float(top3_mass.mean()),
            "max_overclaim_pid": int(np.argmax(piece_occ)),
            "max_overclaim_value": float(piece_occ.max()),
            "min_occ_pid": int(np.argmin(piece_occ)),
            "min_occ_value": float(piece_occ.min()),
            "low_H_adjacency_enrichment": float(enrichment),
            "low_H_adjacency_count": int(adj_both_low),
            "low_H_adjacency_expected": float(expected),
        },
    }
    OUT = ROOT / "output" / "v11_sp" / "marginals_analysis.json"
    with OUT.open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
