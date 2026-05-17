#!/usr/bin/env python3
"""Vol-122 J3 — Spectral piece-graph embedding for CSP variable ordering.

NEW INVENTION: build a piece-compatibility graph (nodes = pieces, edges =
pairs that can be placed adjacent under some rotation). Compute the
graph Laplacian's Fiedler vector. Use it as a PIECE-ORDERING heuristic.

The Fiedler vector partitions the graph into two clusters minimizing the
edge cut. Pieces with similar Fiedler values are "spectrally close" =
likely useful in similar regions of the board. Placing them in similar
positions could exploit this clustering.

This PoC:
1. Builds the compatibility graph (~256 nodes, computing edge weights
   = # rotation pairs that match a color).
2. Computes Fiedler vector via eigsh.
3. Outputs a piece-ordering. Reports the spectral structure.
"""

from __future__ import annotations
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import eigsh


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v

def load_puzzle(csv_path):
    pieces = []
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces.append((parse_color(cols[0]), parse_color(cols[1]),
                               parse_color(cols[2]), parse_color(cols[3])))
            except ValueError: pass
    return pieces

def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def build_compat_graph(pieces):
    """Weight[i][j] = number of (rotation_i, rotation_j, side) combinations
    where piece_i.side_color == piece_j.opposite_side_color (i.e., the
    pieces can be adjacent on some side with matching colors)."""
    n = len(pieces)
    W = lil_matrix((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
            count = 0
            for ri in range(4):
                ei = rotate(pieces[i], ri)
                for rj in range(4):
                    ej = rotate(pieces[j], rj)
                    # 4 possible adjacency directions: i.R↔j.L, i.B↔j.T, i.L↔j.R, i.T↔j.B
                    for (sii, sij) in [(1, 3), (2, 0), (3, 1), (0, 2)]:
                        if ei[sii] == ej[sij] and ei[sii] != 0:
                            count += 1
            W[i, j] = count
            W[j, i] = count
    return W.tocsr()


def laplacian(W):
    """L = D - W, where D = diag(row sums)."""
    n = W.shape[0]
    d = np.array(W.sum(axis=1)).flatten()
    D = lil_matrix((n, n), dtype=np.float64)
    for i in range(n):
        D[i, i] = d[i]
    L = D.tocsr() - W
    return L


def main():
    puzzle_path = Path(sys.argv[1] if len(sys.argv) > 1 else "../data/puzzles/size_16_official_eternity.csv")
    pieces = load_puzzle(puzzle_path)
    n = len(pieces)
    print(f"loaded puzzle: {n} pieces from {puzzle_path.name}")

    print("building compatibility graph...")
    W = build_compat_graph(pieces)
    print(f"  nonzeros: {W.nnz}, avg weight: {W.mean():.2f}")
    print(f"  density: {W.nnz / (n * n):.4f}")

    print("computing Laplacian + 5 smallest eigenvectors...")
    L = laplacian(W)
    # eigsh smallest k eigenvalues
    eigvals, eigvecs = eigsh(L.astype(np.float64), k=5, which='SM')
    print(f"  smallest eigvals: {eigvals}")
    # Fiedler vector = eigenvector of 2nd smallest eigval
    # (smallest is 0, eigenvector = constant)
    fiedler_idx = 1
    fiedler = eigvecs[:, fiedler_idx]
    print(f"  Fiedler eigval: {eigvals[fiedler_idx]:.4f}")

    # Group by sign of Fiedler value (2 spectral clusters)
    pos = [i for i in range(n) if fiedler[i] > 0]
    neg = [i for i in range(n) if fiedler[i] <= 0]
    print(f"  Spectral partition: {len(pos)} pos, {len(neg)} neg")

    # Show distribution of corner/edge/interior pieces in each cluster
    corner_pos, edge_pos, inner_pos = 0, 0, 0
    corner_neg, edge_neg, inner_neg = 0, 0, 0
    for i in range(n):
        n_border = sum(1 for c in pieces[i] if c == 0)
        is_pos = fiedler[i] > 0
        if n_border == 2:
            if is_pos: corner_pos += 1
            else: corner_neg += 1
        elif n_border == 1:
            if is_pos: edge_pos += 1
            else: edge_neg += 1
        else:
            if is_pos: inner_pos += 1
            else: inner_neg += 1
    print(f"  cluster pos: corners={corner_pos} edges={edge_pos} inner={inner_pos}")
    print(f"  cluster neg: corners={corner_neg} edges={edge_neg} inner={inner_neg}")

    # Check 3rd/4th eigenvectors (sub-partitions of border/interior)
    print("\nHigher-order eigenvectors (interior sub-structure):")
    for k_idx in range(2, 5):
        ev = eigvecs[:, k_idx]
        # Restrict to interior pieces only
        interior_pids = [i for i in range(n) if all(c != 0 for c in pieces[i])]
        ev_interior = [(ev[i], i) for i in interior_pids]
        ev_interior.sort()
        # Stats
        ev_min, ev_max = ev_interior[0][0], ev_interior[-1][0]
        # Sub-cluster sizes by sign
        n_pos = sum(1 for v, _ in ev_interior if v > 0)
        n_neg = len(ev_interior) - n_pos
        print(f"  eigval[{k_idx}] = {eigvals[k_idx]:.2f}: interior split = {n_pos} pos / {n_neg} neg, range [{ev_min:.4f}, {ev_max:.4f}]")

    # Save piece ordering by Fiedler value
    order = sorted(range(n), key=lambda i: fiedler[i])
    out_path = puzzle_path.parent / f"{puzzle_path.stem}.fiedler_order.json"
    with open(out_path, 'w') as f:
        json.dump({
            "puzzle": str(puzzle_path),
            "method": "spectral fiedler ordering",
            "n_pieces": n,
            "eigvals_smallest": [float(v) for v in eigvals],
            "fiedler_values": [float(fiedler[i]) for i in order],
            "piece_order": order,
        }, f, indent=2)
    print(f"\nwrote piece ordering to {out_path}")

    # Print spectral neighborhood structure
    print("\nFiedler eigval = lambda_2 → algebraic connectivity / cluster strength.")
    print(f"  lambda_2 = {eigvals[1]:.4f}")
    print("  larger lambda_2 → graph is harder to partition (more uniform connectivity)")
    print("  smaller lambda_2 → strong 2-cluster structure")


if __name__ == "__main__":
    main()
