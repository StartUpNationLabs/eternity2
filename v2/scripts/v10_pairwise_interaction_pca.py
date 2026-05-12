#!/usr/bin/env python3
"""Vol-10 probe #3: PCA on the pairwise piece-interaction matrix.

For each ordered pair of interior pieces (i, j), count the number of
(rot_i, rot_j, adjacency) triples for which the shared edge(s) match.
Adjacency types: piece i is to the W/E/N/S of piece j (4 types). For
each rotation pair (16 of them) and each adjacency type, exactly one
edge-equality must hold.

So M[i,j] ∈ {0..64}: 4 rotations × 4 rotations × 4 adjacency types.

This is the pair-level reduction of Verhaard's "2×2 tilings on a piece
set" metric, which involves 4 pieces. Pair-level is much cheaper
(196² = 38416 entries vs C(196,4) ≈ 60M) and surfaces the same
question: is the interaction matrix low-rank?

If rank(M) ≪ 196: there exist O(1) "interaction archetypes" — vol-9's
Verhaard SA can use the leading PCs as a fitness signal much sharper
than total tile count, and we have an honest geometric handle on the
piece set.

If M is near full-rank: the Selby-Riordan generator engineered the
pairwise level to be incompressible too. Heuristic implication: SA
will have to optimize a high-entropy signal; expect slow convergence.

Outputs: output/v10_math/pairwise_pca.{json,txt}
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


def load_pieces() -> list[str]:
    with PIECES.open() as f:
        s = f.read().strip().strip('"')
    ps = s.split(",")
    assert len(ps) == 256
    return ps


def is_interior(piece: str) -> bool:
    return piece.count("a") == 0


def rotations(piece: str) -> list[tuple[str, str, str, str]]:
    """Return the 4 rotations as (N, E, S, W) tuples.

    Pieces are stored as 4-char strings; project convention is the
    characters list the edges in NESW order. A rotation by k (90° CW)
    shifts NESW → WNES (clockwise rotation of the physical tile moves
    the north edge to the east position, etc.).
    """
    out = []
    n, e, s, w = piece[0], piece[1], piece[2], piece[3]
    sides = [(n, e, s, w)]
    for _ in range(3):
        n, e, s, w = w, n, e, s
        sides.append((n, e, s, w))
    return sides


def pair_score(rots_i: list[tuple[str, str, str, str]],
               rots_j: list[tuple[str, str, str, str]]) -> int:
    """Total over (rot_i, rot_j, adjacency_type) triples where the shared
    edge between pieces i and j matches.

    Adjacency types (4 total): i is W/E/N/S of j.
    - i is W of j: i.E must equal j.W
    - i is E of j: i.W must equal j.E
    - i is N of j: i.S must equal j.N
    - i is S of j: i.N must equal j.S
    """
    score = 0
    for ri in rots_i:
        n_i, e_i, s_i, w_i = ri
        for rj in rots_j:
            n_j, e_j, s_j, w_j = rj
            # 4 adjacency checks
            score += int(e_i == w_j)  # i W-of j
            score += int(w_i == e_j)  # i E-of j
            score += int(s_i == n_j)  # i N-of j
            score += int(n_i == s_j)  # i S-of j
    return score


def main() -> int:
    pieces = load_pieces()
    interior = [(i, p) for i, p in enumerate(pieces) if is_interior(p)]
    assert len(interior) == 196, f"got {len(interior)}"
    n = len(interior)

    rots = [rotations(p) for (_, p) in interior]

    # Precompute compatible counts per edge color (for sanity later)
    M = np.zeros((n, n), dtype=np.int32)

    # The pair score includes self-pair scoring (a piece compared with
    # itself); we compute it for completeness then look at the
    # symmetric off-diagonal.
    for i in range(n):
        # M is symmetric: M[i,j] = M[j,i] because adjacency types pair up
        # (i W-of j ≡ j E-of i, etc.)
        M[i, i] = pair_score(rots[i], rots[i])
        for j in range(i + 1, n):
            s = pair_score(rots[i], rots[j])
            M[i, j] = s
            M[j, i] = s
        if i % 50 == 0:
            print(f"  row {i}/{n}…", file=sys.stderr)

    # Save raw
    np.save(OUT / "pairwise_interaction_matrix.npy", M)
    print(f"matrix saved: shape={M.shape} min={M.min()} max={M.max()} "
          f"mean={M.mean():.3f}", file=sys.stderr)

    # PCA on the symmetric matrix. Center by row mean.
    Mf = M.astype(np.float64)
    # Center: subtract column means (equivalent to row means since symmetric)
    Mc = Mf - Mf.mean(axis=0, keepdims=True)
    # SVD
    U, S, Vt = np.linalg.svd(Mc, full_matrices=False)
    var = S ** 2
    ratio = var / var.sum()
    cumvar = np.cumsum(ratio)

    def k_for(thresh: float) -> int:
        return int(min(np.searchsorted(cumvar, thresh) + 1, len(cumvar)))

    # also do eigendecomp of M (since symmetric, eigenvalues = singular values
    # up to sign of centered version, but here we want the actual eigenstructure
    # of the un-centered M, which is positive-semidefinite-like)
    eigvals = np.linalg.eigvalsh(M.astype(np.float64))
    eigvals = sorted(eigvals, reverse=True)
    top_eigvals = eigvals[:20]

    # Effective rank via stable-rank-like measures
    fro_sq = float((Mf ** 2).sum())
    spec_sq = float((Mf ** 2).max())
    stable_rank = fro_sq / spec_sq if spec_sq > 0 else float("inf")

    # Entropy-rank: exp(-sum p log p) of normalized eigvals
    pos_eigs = np.array([e for e in eigvals if e > 1e-12])
    pos_p = pos_eigs / pos_eigs.sum()
    ent_rank = float(np.exp(-(pos_p * np.log(pos_p)).sum()))

    out = {
        "n_interior_pieces": n,
        "matrix_shape": list(M.shape),
        "matrix_min": int(M.min()),
        "matrix_max": int(M.max()),
        "matrix_mean": float(M.mean()),
        "matrix_std": float(M.std()),
        "diagonal_mean": float(np.diag(M).mean()),
        "offdiag_mean": float((M.sum() - np.diag(M).sum())
                              / (n * n - n)),
        "centered_pca": {
            "var_ratio_top20": [float(r) for r in ratio[:20]],
            "cumvar_top20": [float(c) for c in cumvar[:20]],
            "k_80pct": k_for(0.80),
            "k_90pct": k_for(0.90),
            "k_95pct": k_for(0.95),
            "k_99pct": k_for(0.99),
        },
        "uncentered_eigenvalues_top20": [float(e) for e in top_eigvals],
        "stable_rank": float(stable_rank),
        "participation_rank": ent_rank,
    }
    with (OUT / "pairwise_pca.json").open("w") as f:
        json.dump(out, f, indent=2)

    # human-readable
    lines = []
    lines.append("=== vol-10 probe #3: pairwise interaction PCA ===")
    lines.append("")
    lines.append(f"Interior pieces: {n}")
    lines.append(f"Matrix entries: M[i,j] = # of (rot_i, rot_j, adjacency) "
                 "triples matching")
    lines.append(f"  range: [{M.min()}, {M.max()}], "
                 f"mean={M.mean():.3f} std={M.std():.3f}")
    lines.append(f"  diagonal mean: {np.diag(M).mean():.3f}  "
                 f"off-diag mean: {(M.sum()-np.diag(M).sum())/(n*n-n):.3f}")
    lines.append("")
    lines.append("--- Centered PCA on M (n=196) ---")
    lines.append("PC | var ratio | cumvar")
    for i in range(20):
        lines.append(f"  {i+1:3d} | {ratio[i]:8.4f}  | {cumvar[i]:8.4f}")
    lines.append("")
    lines.append(f"k for 80%: {k_for(0.80):3d}    "
                 f"90%: {k_for(0.90):3d}    "
                 f"95%: {k_for(0.95):3d}    "
                 f"99%: {k_for(0.99):3d}")
    lines.append("")
    lines.append(f"Stable rank (Frobenius^2 / spectral^2): {stable_rank:.2f}")
    lines.append(f"Participation rank (entropic): {ent_rank:.2f}")
    lines.append("")
    lines.append("Top 20 eigenvalues of un-centered M:")
    for i, e in enumerate(top_eigvals):
        lines.append(f"  λ_{i+1:2d} = {e:12.2f}")
    lines.append("")

    # interpretation
    k80 = k_for(0.80)
    k95 = k_for(0.95)
    lines.append("--- interpretation ---")
    lines.append("")
    iid_baseline = n / 4  # rough heuristic: full-rank → k80 ≈ 0.8 * n
    lines.append(f"Random full-rank baseline: k80 ≈ {0.8 * n:.0f}, "
                 f"k95 ≈ {0.95 * n:.0f}")
    lines.append(f"This matrix:               k80 = {k80}, k95 = {k95}")
    lines.append("")
    if k80 < 20:
        lines.append("STRONG LOW-RANK STRUCTURE: the pairwise-interaction matrix")
        lines.append(f"is compressible to ~{k80} dimensions. There exist a small")
        lines.append("number of 'interaction archetypes' that explain most of")
        lines.append("the pairwise behaviour. Vol-9's Verhaard SA can project")
        lines.append("piece sets onto the top-k PCs and optimize the projection;")
        lines.append("expect much faster SA convergence than total-tile-count.")
    elif k80 < 50:
        lines.append("MODERATE LOW-RANK STRUCTURE: pairwise matrix is")
        lines.append(f"compressible to ~{k80}/{n} dimensions (~{100*k80/n:.0f}%).")
        lines.append("Some interaction archetypes exist; SA can benefit from a")
        lines.append("projected fitness signal but the gain will be modest.")
    elif k80 < int(0.5 * n):
        lines.append("WEAK LOW-RANK STRUCTURE: pairwise matrix is mildly")
        lines.append(f"compressible to ~{k80}/{n} dimensions (~{100*k80/n:.0f}%).")
        lines.append("The pair-level interaction landscape is closer to flat")
        lines.append("than to clustered. SA must rely on collective higher-")
        lines.append("order signals; pair-level projection is unlikely to help.")
    else:
        lines.append("NO LOW-RANK STRUCTURE: pairwise matrix is essentially")
        lines.append(f"full-rank ({k80}/{n} dims to capture 80%). The Selby-")
        lines.append("Riordan generator engineered the puzzle to be incompressible")
        lines.append("at the pair level too. Vol-9 SA on total tile count is")
        lines.append("the best you can do at this granularity; expect slow")
        lines.append("convergence and no shortcut from spectral projection.")
    lines.append("")
    lines.append("Note: 'compressibility' here is *linear*. Non-linear structure")
    lines.append("(e.g. via kernel PCA or autoencoders on the same matrix) is")
    lines.append("NOT ruled out by this probe.")
    lines.append("")

    txt = "\n".join(lines)
    print(txt)
    with (OUT / "pairwise_pca.txt").open("w") as f:
        f.write(txt + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
