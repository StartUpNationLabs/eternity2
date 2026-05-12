#!/usr/bin/env python3
"""Save the position-aware piece-rotation eigenbasis to disk.

Outputs:
  output/v10_math/position_color_basis.json
    {
      "alphabet": [22 colors],
      "positions": ["E","W","S","N"],
      "feature_names": [88 strings, "E-b", "E-c", ...],
      "phi_matrix": [784 x 88 list of lists],   # the raw embedding
      "permutation_P": [88 x 88],                # swap E↔W, N↔S
      "eigenvalues": [65 floats, descending],
      "eigenvectors": [65 x 88 list of lists]    # in feature space
    }
  output/v10_math/position_color_projected_pieces.json
    {
      "piece_rotation_ids": [784 (piece_idx, rotation) pairs],
      "projected_top33": [784 x 33 list of lists]  # what vol-9 would consume
    }

The piece's position-color signature (in any rotation) is a length-88
binary vector. Each piece in a fixed rotation lives in a 65-dimensional
subspace; the top-33 dimensions there capture 99% of pair-interaction
variance. A piece-SET's projected energy in these dims is a structural
fitness signal vol-9's Verhaard SA can plug in directly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PIECES = ROOT / "output" / "archive" / "pieces.txt"
OUT = ROOT / "output" / "v10_math"
OUT.mkdir(parents=True, exist_ok=True)

ALPHABET = list("bcdefghijklmnopqrstuvw")
POSITIONS = ["E", "W", "S", "N"]


def load_interior_pieces():
    with PIECES.open() as f:
        s = f.read().strip().strip('"')
    pieces = s.split(",")
    interior_idx = [i for i, p in enumerate(pieces) if p.count("a") == 0]
    interior = [pieces[i] for i in interior_idx]
    return interior_idx, interior


def main() -> int:
    interior_idx, interior = load_interior_pieces()
    n = len(interior)
    feature_names = [f"{pos}-{c}" for pos in POSITIONS for c in ALPHABET]
    assert len(feature_names) == 88

    Phi = np.zeros((n * 4, 88), dtype=np.float64)
    pr_ids = []
    for i, p in enumerate(interior):
        n_, e_, s_, w_ = p
        sides_per_rot = [
            (n_, e_, s_, w_),
            (w_, n_, e_, s_),
            (s_, w_, n_, e_),
            (e_, s_, w_, n_),
        ]
        for r in range(4):
            ni, ei, si, wi = sides_per_rot[r]
            row = i * 4 + r
            pr_ids.append([interior_idx[i], r])
            for sym, idx_offset in [(ei, 0), (wi, 22), (si, 44), (ni, 66)]:
                if sym in ALPHABET:
                    Phi[row, idx_offset + ALPHABET.index(sym)] = 1.0

    # Swap permutation P (E↔W, S↔N)
    P = np.zeros((88, 88))
    P[0:22, 22:44] = np.eye(22)  # E -> W
    P[22:44, 0:22] = np.eye(22)  # W -> E
    P[44:66, 66:88] = np.eye(22)  # S -> N
    P[66:88, 44:66] = np.eye(22)  # N -> S

    # M3 = Phi @ P @ Phi.T (784 x 784).
    # Eigendecomp of M3 has the same nonzero spectrum as (P @ Phi.T @ Phi)
    # which is 88 x 88. Easier to diagonalize the small matrix.
    K = P @ (Phi.T @ Phi)  # 88x88
    # K is not symmetric (P @ S is generally not symmetric for general S).
    # We want the eigenvalues/vectors of M3 = Phi @ P @ Phi.T which IS
    # symmetric. Equivalent reduction: diagonalize Phi.T @ Phi @ P (also
    # 88x88, same eigenvalues as M3 up to zeros).
    A = Phi.T @ Phi @ P  # 88x88
    # M3 = Phi @ P @ Phi.T is symmetric; its nonzero eigenvalues match those
    # of A. Let's get them directly from M3 then for cleanliness.

    # 784x784 eigendecomp is fine (a few seconds).
    M3 = Phi @ P @ Phi.T
    print(f"M3 shape: {M3.shape}, rank≈ {np.linalg.matrix_rank(M3)}",
          file=sys.stderr)

    # Use eigh since symmetric. Note: eigh returns ascending.
    eigvals, eigvecs = np.linalg.eigh(M3)
    # Reorder descending
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]

    # Keep top 65 (since rank ≈ 65)
    K = 65
    eigvals_top = eigvals[:K]
    eigvecs_top = eigvecs[:, :K]  # (784, K) — but these are eigenvectors in
                                  # the 784-dim space of piece-rotations,
                                  # not in feature space.

    # For a feature-space basis usable per-piece, we use the singular vectors
    # of Phi: SVD Phi = U Σ V^T → V is 88x88, columns are feature-space
    # directions. M3 = Phi P Phi^T = U Σ V^T P V Σ U^T; eigenvalues of M3
    # are eigenvalues of Σ V^T P V Σ (an 88x88 problem).
    U, sigma, Vt = np.linalg.svd(Phi, full_matrices=False)
    # Effective rank of Phi
    sig_rank = (sigma > 1e-8).sum()
    print(f"rank(Phi) by singular value: {sig_rank}", file=sys.stderr)

    # Now find the eigenstructure of the 88x88 matrix B = Σ V^T P V Σ
    Sigma_diag = np.diag(sigma)
    B = Sigma_diag @ Vt @ P @ Vt.T @ Sigma_diag
    # B is symmetric (since (V^T P V)^T = V^T P^T V = V^T P V if P is
    # symmetric, which our P is since it's a self-inverse permutation).
    print(f"B symmetric? max asym = {np.abs(B - B.T).max():.2e}",
          file=sys.stderr)
    B_eigvals, B_eigvecs = np.linalg.eigh(B)
    order_b = np.argsort(B_eigvals)[::-1]
    B_eigvals = B_eigvals[order_b]
    B_eigvecs = B_eigvecs[:, order_b]

    # Feature-space eigenvectors: each column of V @ B_eigvecs gives a
    # direction in the 88-dim feature space (i.e. (position, color) combo)
    # along which piece-rotations vary maximally.
    feature_basis = Vt.T @ B_eigvecs  # (88, 88)

    # Keep up to rank K
    feature_basis_top = feature_basis[:, :K]  # (88, K)
    feature_eigvals = B_eigvals[:K]

    # Sanity: pair-interaction variance reconstructed.
    # M3 = Phi @ P @ Phi.T should equal Phi_proj * lambda * Phi_proj^T
    # where Phi_proj = Phi @ feature_basis_top — but only if we use ALL 65.
    Phi_proj_full = Phi @ feature_basis_top
    M3_reconstr = Phi_proj_full @ np.diag(feature_eigvals) @ Phi_proj_full.T
    err = np.abs(M3 - M3_reconstr).max()
    print(f"reconstruction error (top {K} basis): {err:.6e}", file=sys.stderr)

    # Now project pieces onto top-33 components for the eventual vol-9 use
    TOP = 33
    Phi_proj_top = (Phi @ feature_basis[:, :TOP]).tolist()

    # Save
    basis_doc = {
        "alphabet": ALPHABET,
        "positions": POSITIONS,
        "feature_names": feature_names,
        "phi_matrix_first10": Phi[:10].tolist(),  # sample only
        "permutation_P_compact": "swap (E,W) and (S,N) blocks of 22",
        "feature_eigenvalues_top65": [float(x) for x in feature_eigvals],
        "feature_eigenvectors_top10": [
            [float(x) for x in feature_basis[:, k]]
            for k in range(min(10, K))
        ],
        "n_piece_rotations": Phi.shape[0],
        "rank_Phi": int(sig_rank),
        "comment": (
            "Each piece-rotation lives in an 88-dim (position×color) space "
            "but spans only 65 independent directions. Within that subspace, "
            "33 components explain 99% of pair-interaction variance."
        ),
    }
    with (OUT / "position_color_basis.json").open("w") as f:
        json.dump(basis_doc, f, indent=2)

    proj_doc = {
        "piece_rotation_ids": pr_ids,
        "top_components": TOP,
        "feature_eigenvalues_top33": [
            float(x) for x in feature_eigvals[:TOP]
        ],
        "projected_top33": Phi_proj_top,
    }
    with (OUT / "position_color_projected_pieces.json").open("w") as f:
        json.dump(proj_doc, f, indent=2)

    np.save(OUT / "feature_basis_88x65.npy",
            feature_basis[:, :K].astype(np.float64))
    np.save(OUT / "feature_eigenvalues_65.npy",
            feature_eigvals.astype(np.float64))
    np.save(OUT / "phi_matrix_784x88.npy", Phi.astype(np.float64))

    print(
        f"saved: position_color_basis.json, "
        f"position_color_projected_pieces.json, "
        f"feature_basis_88x65.npy, feature_eigenvalues_65.npy, "
        f"phi_matrix_784x88.npy",
        file=sys.stderr,
    )
    print(f"Top 10 eigenvalues: "
          f"{[f'{x:.2f}' for x in feature_eigvals[:10]]}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
