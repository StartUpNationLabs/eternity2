#!/usr/bin/env python3
"""Vol-65 — Spectral analysis of the piece-side-compatibility graph.

Compute eigenvalues + eigenvectors of the (1024 × 1024) adjacency
matrix of G_PS_rotaware. The spectral gap and dominant eigenvectors
reveal natural cluster structure of piece-sides.

Hypothesis: if there's a clear spectral gap (e.g., λ_2 / λ_1 < 0.5),
the piece-sides decompose into natural communities. These communities
may correspond to spatial regions in the assembled board.

Additionally compute:
- Algebraic connectivity λ_2 of the Laplacian.
- Fiedler vector for graph partitioning.
- Modularity Q = clustering coefficient of partitioning.

Output: eigenvalue spectrum + saving the Fiedler-partition assignment
for each piece-side.
"""

import collections
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def main():
    with open("output/vol-65/ps_graph_rotaware.json") as f:
        g = json.load(f)

    n_nodes = g["n_nodes_total"]  # 1024
    edges = g["edges"]
    print(f"Loaded rotation-aware PS-graph: {n_nodes} nodes, {len(edges)} edges")

    # Build sparse adjacency
    rows = []; cols = []; data = []
    for u, v, _col in edges:
        rows.append(u); cols.append(v); data.append(1.0)
        rows.append(v); cols.append(u); data.append(1.0)
    A = sp.coo_matrix((data, (rows, cols)), shape=(n_nodes, n_nodes)).tocsr()
    print(f"Adjacency matrix: nnz={A.nnz}")

    # Degree
    deg = np.asarray(A.sum(axis=1)).flatten()
    print(f"Degree: min={int(deg.min())}, median={int(np.median(deg))}, "
          f"max={int(deg.max())}, # zero-degree: {int(np.sum(deg == 0))}")

    # Compute top-k eigenvalues of A (largest magnitude)
    print("\nComputing top-10 eigenvalues of adjacency matrix...")
    k = 10
    eigvals, eigvecs = spla.eigsh(A, k=k, which='LM')
    # sort by abs descending
    order = np.argsort(-np.abs(eigvals))
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    print(f"Top-{k} eigenvalues (by |λ|):")
    for i, lam in enumerate(eigvals):
        print(f"  λ_{i+1} = {lam:.4f}")

    # Spectral gap
    print(f"\nλ_1 = {eigvals[0]:.4f}")
    print(f"λ_2 = {eigvals[1]:.4f}")
    print(f"Spectral gap: λ_1 / λ_2 = {eigvals[0]/eigvals[1]:.4f}")
    print(f"            : |λ_1 - λ_2| = {abs(eigvals[0]-eigvals[1]):.4f}")
    print(f"            : (λ_1 - λ_2) / λ_1 = "
          f"{(eigvals[0]-eigvals[1])/eigvals[0]:.4f}")

    # Compute normalized Laplacian for community detection
    # L_norm = I - D^(-1/2) A D^(-1/2)
    # Use only non-isolated nodes
    nonzero_mask = deg > 0
    nonzero_idx = np.where(nonzero_mask)[0]
    A_sub = A[nonzero_idx, :][:, nonzero_idx]
    deg_sub = deg[nonzero_mask]
    D_inv_sqrt = sp.diags(1.0 / np.sqrt(deg_sub))
    L_norm = sp.eye(len(nonzero_idx)) - D_inv_sqrt @ A_sub @ D_inv_sqrt

    print(f"\nNormalized Laplacian: {L_norm.shape[0]}×{L_norm.shape[1]}")
    print("Computing bottom-5 eigenvalues of L_norm (small = clusters)...")
    eigvals_L, eigvecs_L = spla.eigsh(L_norm, k=5, which='SM')
    eigvals_L.sort()
    print(f"Bottom-5 L_norm eigenvalues:")
    for i, lam in enumerate(eigvals_L):
        print(f"  μ_{i+1} = {lam:.6f}")
    # λ_1 = 0 (constant vector), λ_2 = algebraic connectivity = Fiedler value
    print(f"\nAlgebraic connectivity μ_2 = {eigvals_L[1]:.6f}")

    # Fiedler partition
    fiedler = eigvecs_L[:, 1]  # second smallest eigvec
    pos_part = sum(1 for v in fiedler if v > 0)
    neg_part = sum(1 for v in fiedler if v <= 0)
    print(f"Fiedler partition: {pos_part} nodes positive, {neg_part} negative")

    # Map back to piece-sides
    print(f"\nPiece-side assignment (cluster 0 vs 1) for non-isolated nodes:")
    cluster_pieces = {0: collections.Counter(), 1: collections.Counter()}
    for local_idx, fid in enumerate(fiedler):
        node = nonzero_idx[local_idx]
        piece = node // 4
        cluster = 0 if fid > 0 else 1
        cluster_pieces[cluster][piece] += 1

    # How many pieces have ALL their sides in one cluster?
    pieces_one_cluster = 0
    pieces_split = 0
    pieces_in_each = {0: 0, 1: 0}
    for p in range(256):
        c0 = cluster_pieces[0].get(p, 0)
        c1 = cluster_pieces[1].get(p, 0)
        if c0 + c1 == 0:
            continue
        if c0 == 0:
            pieces_in_each[1] += 1; pieces_one_cluster += 1
        elif c1 == 0:
            pieces_in_each[0] += 1; pieces_one_cluster += 1
        else:
            pieces_split += 1
    print(f"  Pieces with all sides in one cluster: {pieces_one_cluster}")
    print(f"    cluster 0 (Fiedler > 0): {pieces_in_each[0]} pieces")
    print(f"    cluster 1 (Fiedler ≤ 0): {pieces_in_each[1]} pieces")
    print(f"  Pieces with sides SPLIT between clusters: {pieces_split}")

    # Save eigenvalues + Fiedler partition
    Path("output/vol-65").mkdir(parents=True, exist_ok=True)
    np.savez("output/vol-65/ps_spectrum.npz",
             eigvals=eigvals, eigvals_L=eigvals_L,
             fiedler=fiedler, nonzero_idx=nonzero_idx)
    print(f"\nSaved spectrum to output/vol-65/ps_spectrum.npz")


if __name__ == "__main__":
    main()
