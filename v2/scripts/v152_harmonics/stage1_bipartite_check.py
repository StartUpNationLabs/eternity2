#!/usr/bin/env python3
"""V152-T1d — Test if SOME natural 2-coloring of pieces admits a
perfect bipartite matching in the demand graph.

Try several candidate 2-colorings:
  a) Random 128-128 splits (5 random trials).
  b) Border vs interior pieces (4+56=60 vs 196 — wrong size, skip).
  c) "Rare-bearing" vs "no-rare" pieces.
  d) Parity of piece-id (pid % 2) — sanity.

For each: build the bipartite subgraph of the demand graph (only edges
crossing the 2-coloring), check if a perfect matching exists.
"""

from __future__ import annotations
import argparse
import random
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts/v152_harmonics"))
from stage1_match import load_canonical_pieces, build_demand_graph


def filter_bipartite(G, color_of_piece):
    """Remove edges in G that connect same-colored pieces."""
    G_bip = G.copy()
    for u, v in list(G_bip.edges()):
        if color_of_piece[u[0]] == color_of_piece[v[0]]:
            G_bip.remove_edge(u, v)
    return G_bip


def check_perfect_matching(G_bip, n_total):
    M = nx.algorithms.matching.max_weight_matching(G_bip, maxcardinality=True)
    return len(M), len(M) * 2 == n_total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    ap.add_argument("--n-random", type=int, default=5)
    args = ap.parse_args()

    size, pieces = load_canonical_pieces(args.puzzle)
    print(f"[v152-t1d] puzzle: {size}×{size}, {len(pieces)} pieces", flush=True)
    G = build_demand_graph(pieces)
    n_total = G.number_of_nodes()
    print(f"[v152-t1d] demand graph: |V|={n_total} |E|={G.number_of_edges()}", flush=True)

    colorings = {}

    # (a) Random 128-128 splits.
    rng = random.Random(42)
    for trial in range(args.n_random):
        pids = list(range(len(pieces)))
        rng.shuffle(pids)
        color = {pid: 0 if i < 128 else 1 for i, pid in enumerate(pids)}
        colorings[f"random_{trial}"] = color

    # (c) Rare-bearing 2-coloring (piece has any color 1-5).
    rare_color = {pid: int(any(1 <= c <= 5 for c in pieces[pid])) for pid in range(len(pieces))}
    # Check 128-128.
    n_rare = sum(rare_color.values())
    print(f"[v152-t1d] rare-bearing count: {n_rare} (need 128 for grid)")
    colorings["rare-bearing"] = rare_color

    # (d) Piece-id parity.
    pid_par = {pid: pid % 2 for pid in range(len(pieces))}
    colorings["pid-parity"] = pid_par

    # (e) Even-color-sum-parity: sum of colors mod 2.
    csum = {pid: sum(c for c in pieces[pid] if c != 0) % 2 for pid in range(len(pieces))}
    colorings["color-sum-parity"] = csum
    print(f"[v152-t1d] color-sum-parity bal: {sum(csum.values())}/{len(pieces)}")

    # (f) Bipartite-by-degree (4-degree pieces alternate with 3-degree).
    # Won't be 128-128 directly. Skip.

    print(f"\n[v152-t1d] testing {len(colorings)} colorings for bipartite perfect matching:")
    for name, color in colorings.items():
        sizes = (sum(1 for v in color.values() if v == 0),
                 sum(1 for v in color.values() if v == 1))
        G_bip = filter_bipartite(G, color)
        M, perfect = check_perfect_matching(G_bip, n_total)
        print(f"  {name}: split {sizes}, |E_bip|={G_bip.number_of_edges()}, "
              f"|M|={M}, perfect={perfect}")


if __name__ == "__main__":
    main()
