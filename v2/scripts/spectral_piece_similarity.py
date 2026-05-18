#!/usr/bin/env python3
"""SPECTRAL-SWAP — Phase 1: compute the piece-similarity matrix and its
eigenvectors for canonical Eternity II.

S_{ij} = number of (rot_i, rot_j, side_i, side_j) tuples where piece i
in rotation rot_i has edge color on side_i matching piece j in rotation
rot_j on side_j. (over all 4 sides × 4 rotations × 4 rotations = 64).

This gives a 256×256 matrix. We compute the top-16 eigenvectors and
bucket pieces into clusters by sign patterns.

Output: spectral clusters table, eigenvalue spectrum, sample similar/
dissimilar piece pairs. Saved as JSON for later use by SPECTRAL-SWAP
ALNS operator.
"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
PUZZLE_CSV = REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv"
OUT_DIR = REPO / "output" / "vol-125" / "spectral"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BORDER = 65535


def parse_color(s: str) -> int:
    """CSV stores colors as binary strings; BORDER is 65535."""
    v = int(s.strip(), 2)
    return v


def load_pieces() -> list[tuple[int, int, int, int]]:
    """Return list of 256 pieces, each a 4-tuple (N, E, S, W) of colors."""
    pieces = []
    with open(PUZZLE_CSV) as f:
        reader = csv.reader(f)
        next(reader)  # skip "16"
        for row in reader:
            # CSV row: N, E, S, W (binary strings) + 3 hint columns
            N, E, S, W = (parse_color(row[i]) for i in range(4))
            pieces.append((N, E, S, W))
    if len(pieces) != 256:
        raise RuntimeError(f"expected 256 pieces, got {len(pieces)}")
    return pieces


def rotate(piece: tuple, r: int) -> tuple:
    """Rotate piece by r * 90° clockwise. r in {0,1,2,3}."""
    # NESW after rotation. R90: new N = old W, new E = old N, etc.
    N, E, S, W = piece
    if r == 0: return (N, E, S, W)
    if r == 1: return (W, N, E, S)
    if r == 2: return (S, W, N, E)
    if r == 3: return (E, S, W, N)
    raise ValueError(r)


def build_similarity(pieces: list) -> np.ndarray:
    """S[i,j] = number of (rot_i, rot_j, side_i, side_j) tuples where
    piece i's side_i in rot_i color == piece j's side_j in rot_j color,
    AND those colors are not BORDER."""
    n = len(pieces)
    S = np.zeros((n, n), dtype=np.int32)
    # Pre-compute all rotated edges per piece.
    rotated_edges = []  # rotated_edges[piece_id][rot] = (N,E,S,W)
    for p in pieces:
        rotated_edges.append([rotate(p, r) for r in range(4)])
    # Build S.
    for i in range(n):
        for j in range(n):
            if i == j: continue
            count = 0
            for ri in range(4):
                ei = rotated_edges[i][ri]
                for rj in range(4):
                    ej = rotated_edges[j][rj]
                    for si in range(4):
                        for sj in range(4):
                            ci = ei[si]
                            cj = ej[sj]
                            if ci != BORDER and cj != BORDER and ci == cj:
                                count += 1
            S[i, j] = count
    return S


def main():
    print(f"Loading pieces from {PUZZLE_CSV}...", flush=True)
    pieces = load_pieces()
    print(f"  loaded {len(pieces)} pieces", flush=True)

    print("Building 256x256 piece-similarity matrix...", flush=True)
    S = build_similarity(pieces)
    print(f"  S sum = {S.sum()}, mean = {S.mean():.1f}, max = {S.max()}", flush=True)

    # Spectral decomposition. S is symmetric (similarity, undirected).
    print("Computing eigenvectors via numpy.linalg.eigh...", flush=True)
    S_sym = (S + S.T) / 2
    eigvals, eigvecs = np.linalg.eigh(S_sym)
    # eigh returns ascending; reverse for descending.
    eigvals = eigvals[::-1]
    eigvecs = eigvecs[:, ::-1]
    print(f"  top eigenvalues: {eigvals[:10].tolist()}", flush=True)

    # Bucket pieces by sign of top-3 eigenvectors → 8 clusters.
    top_k = 4
    signs = (eigvecs[:, :top_k] > 0).astype(int)  # 256 × top_k
    # Convert sign-pattern to bucket id.
    cluster_id = np.zeros(256, dtype=int)
    for i in range(256):
        cluster_id[i] = int("".join(str(x) for x in signs[i]), 2)

    cluster_counts = Counter(cluster_id.tolist())
    print(f"  {top_k}-bit sign-pattern clusters: {dict(cluster_counts.most_common())}",
          flush=True)

    # Top similar pieces (by S[i,j] excluding diagonal)
    flat = S_sym.copy()
    np.fill_diagonal(flat, 0)
    top_idx = np.unravel_index(np.argsort(flat.ravel())[::-1][:10], flat.shape)
    print("\nTop 10 most-similar piece pairs:", flush=True)
    for a, b in zip(top_idx[0][:10], top_idx[1][:10]):
        if a < b:
            print(f"  piece {a:3d} ↔ piece {b:3d}: S = {S_sym[a,b]}", flush=True)

    # Save data.
    out = {
        "matrix_sum": int(S.sum()),
        "matrix_mean": float(S.mean()),
        "top_10_eigenvalues": eigvals[:10].tolist(),
        "cluster_id_per_piece": cluster_id.tolist(),
        "cluster_counts": {str(k): v for k, v in cluster_counts.items()},
        "top_eigvecs_norm": np.linalg.norm(eigvecs[:, :top_k], axis=0).tolist(),
    }
    out_path = OUT_DIR / "piece_spectral.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved spectral analysis to {out_path}", flush=True)

    # Also save the raw S matrix as npz.
    npz_path = OUT_DIR / "piece_similarity.npz"
    np.savez_compressed(npz_path, S=S, eigvals=eigvals, eigvecs=eigvecs)
    print(f"Saved S matrix + eigendata to {npz_path}", flush=True)


if __name__ == "__main__":
    main()
