#!/usr/bin/env python3
"""Vol-10 probe #1: PCA on the 256-piece histogram point-cloud.

Each piece is embedded as a length-23 histogram vector (count of each color
across its 4 edges, order ignored). Stacks into a 256×23 matrix and runs PCA.

Question: if the first 2-3 PCs capture >80% variance, there is hidden
low-dimensional structure exploitable for piece-set selection / grouping.
If the spectrum is flat, that itself is evidence the Selby-Riordan generator
deliberately flattened the embedding (which agrees with vol-7's M1 finding
about generator-designed flatness on 2×3 tileability).

Run:
    python3 scripts/v10_pca_piece_cloud.py

Outputs:
    output/v10_math/pca_piece_cloud.json
    output/v10_math/pca_piece_cloud.txt (human-readable)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PIECES = ROOT / "output" / "archive" / "pieces.txt"
OUT = ROOT / "output" / "v10_math"
OUT.mkdir(parents=True, exist_ok=True)

# 23 chars: 'a' is the border / gray, 'b'..'w' are the 22 interior colors.
ALPHABET = list("abcdefghijklmnopqrstuvw")
assert len(ALPHABET) == 23


def load_pieces() -> list[str]:
    with PIECES.open() as f:
        s = f.read().strip().strip('"')
    ps = s.split(",")
    assert len(ps) == 256, f"expected 256 pieces, got {len(ps)}"
    assert all(len(p) == 4 for p in ps)
    return ps


def histogram_matrix(pieces: list[str]) -> np.ndarray:
    """256 × 23 matrix; row i = histogram of piece i over the 23-char alphabet."""
    X = np.zeros((len(pieces), len(ALPHABET)), dtype=np.float64)
    for i, p in enumerate(pieces):
        c = Counter(p)
        for j, a in enumerate(ALPHABET):
            X[i, j] = c.get(a, 0)
    return X


def classify(piece: str) -> str:
    n_border = piece.count("a")
    if n_border == 2:
        return "corner"
    if n_border == 1:
        return "edge"
    return "interior"


def main() -> int:
    pieces = load_pieces()
    klass = [classify(p) for p in pieces]
    n_corner = klass.count("corner")
    n_edge = klass.count("edge")
    n_interior = klass.count("interior")
    assert n_corner == 4, f"expected 4 corners, got {n_corner}"
    assert n_edge == 56, f"expected 56 edges, got {n_edge}"
    assert n_interior == 196, f"expected 196 interior, got {n_interior}"

    X_full = histogram_matrix(pieces)

    # also a 196 × 22 version dropping border/corner pieces and the 'a' column,
    # since those rows live on a different sub-manifold (have non-zero 'a').
    interior_mask = np.array([k == "interior" for k in klass])
    X_int = X_full[interior_mask, 1:]  # drop column 0 ('a')
    assert X_int.shape == (196, 22)

    def pca_report(X: np.ndarray, label: str) -> dict:
        Xc = X - X.mean(axis=0, keepdims=True)
        # use SVD; full=False is fine since we want all components
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
        # eigenvalues of covariance = S^2 / (n-1); we only need ratios
        var = (S ** 2)
        ratio = var / var.sum()
        cumvar = np.cumsum(ratio)
        # find smallest k with cumvar[k-1] >= threshold
        def k_for(thresh: float) -> int:
            idx = np.searchsorted(cumvar, thresh) + 1
            return int(min(idx, len(cumvar)))
        d = {
            "label": label,
            "shape": list(X.shape),
            "singular_values": [float(s) for s in S],
            "var_ratio": [float(r) for r in ratio],
            "cumvar": [float(c) for c in cumvar],
            "k_80pct": k_for(0.80),
            "k_90pct": k_for(0.90),
            "k_95pct": k_for(0.95),
            "var_ratio_top3": [float(r) for r in ratio[:3]],
            "loading_top1_abs": [float(v) for v in np.abs(Vt[0])],
        }
        return d

    r_full = pca_report(X_full, "all_256_pieces_full_23dim")
    r_int = pca_report(X_int, "interior_196_pieces_22dim")

    # also project interior cloud onto first 2 PCs and dump as scatter coords
    Xc = X_int - X_int.mean(axis=0, keepdims=True)
    _, _, Vt_int = np.linalg.svd(Xc, full_matrices=False)
    coords_2d = (Xc @ Vt_int.T[:, :2]).tolist()

    result = {
        "alphabet": ALPHABET,
        "class_counts": {"corner": n_corner, "edge": n_edge, "interior": n_interior},
        "full_23dim": r_full,
        "interior_22dim": r_int,
        "interior_2d_coords": coords_2d,
    }

    with (OUT / "pca_piece_cloud.json").open("w") as f:
        json.dump(result, f, indent=2)

    # human-readable
    lines = []
    lines.append("=== vol-10 probe #1: PCA on piece histogram cloud ===")
    lines.append("")
    lines.append(f"Class counts: corner={n_corner}, edge={n_edge}, interior={n_interior}")
    lines.append("")
    for tag, r in [("ALL 256 × 23", r_full), ("INTERIOR 196 × 22", r_int)]:
        lines.append(f"--- {tag} ---")
        lines.append("PC | var ratio | cumvar")
        for i, (vr, cv) in enumerate(zip(r["var_ratio"][:10], r["cumvar"][:10])):
            lines.append(f"  {i+1:2d} | {vr:8.4f}  | {cv:8.4f}")
        lines.append(f"k for 80%: {r['k_80pct']}    90%: {r['k_90pct']}    95%: {r['k_95pct']}")
        lines.append(f"top-3 var-ratio sum: {sum(r['var_ratio_top3']):.4f}")
        lines.append("")

    interp = []
    interp.append("--- interpretation ---")
    k80_int = r_int["k_80pct"]
    top3_int = sum(r_int["var_ratio_top3"])
    if k80_int <= 3:
        interp.append(f"Interior cloud is LOW-DIMENSIONAL: {k80_int} PCs cover 80%.")
        interp.append("→ hidden structure exploitable for piece grouping.")
    elif k80_int <= 6:
        interp.append(f"Interior cloud is MODERATELY structured: {k80_int} PCs cover 80%.")
        interp.append("→ partial low-dim structure; clustering plausible but not dominant.")
    else:
        interp.append(f"Interior cloud is HIGH-DIMENSIONAL: needs {k80_int} PCs for 80%.")
        interp.append("→ Selby-Riordan flatness hypothesis SUPPORTED: generator engineered")
        interp.append("  the cloud to be roughly isotropic, defeating histogram-based heuristics.")
        interp.append("→ this matches vol-7 M1 finding (2×3 tileability flattened 22x vs E1).")
    interp.append("")
    interp.append(f"top-3 PCs explain {top3_int*100:.1f}% of variance")
    interp.append("(compare: random 22-uniform points would give 3/22 = 13.6%;")
    interp.append(" a strong 3-cluster structure would give >70%)")
    lines.extend(interp)

    txt = "\n".join(lines)
    print(txt)
    with (OUT / "pca_piece_cloud.txt").open("w") as f:
        f.write(txt + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
