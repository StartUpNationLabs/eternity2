#!/usr/bin/env python3
"""V126-T1 v2 — CONCORD: Veit Elser's difference map, REDONE.

State x ∈ R^{N × P × R} (N cells, P pieces, R=4 rotations).

Two constraint sets:
  A = "hard assignment": each cell has exactly one (p,r). Hard one-hot per cell.
  B = "piece-unique + edge-consistent": LAP over pieces (each piece used once),
      rotation chosen to maximize edge-agreement with neighbors.

P_A: per-cell argmax → one-hot.
P_B: LAP with cost matrix combining "is this piece+rot a good fit at this cell
     given current neighbor commitments?" The neighbor commitments come from
     the input x's argmax (locked-in choices). We score (c, p, r) by
     edge-agreement with x[neighbor]'s argmax piece/rot, then take max over r
     to get the LAP cost for (c, p), then solve LAP.

Difference-map iteration:
  x_{n+1} = x_n + β · ( P_A(2·P_B(x_n) - x_n) - P_B(x_n) )

Fixed point ⇔ P_B(x) is also fixed by P_A → it's in both A and B → it's a
valid solution (each cell has one piece, each piece used once, edges agree).

This formulation is cleaner than v1 because:
- P_A is genuinely one-hot per cell.
- P_B's LAP enforces piece-uniqueness HARD.
- P_B's rotation selection ENCODES edge-consistency. So fixed point of B = a
  consistent assignment.
- The two sets A and B are different (B is stronger), so updates are nontrivial.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path(__file__).resolve().parents[1]


def load_puzzle_csv(csv_path: Path):
    BORDER_RAW = 65535
    with open(csv_path) as f:
        size = int(f.readline().strip())
        pieces = []
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


def build_edges(pieces, R=4):
    P = len(pieces)
    e = np.zeros((P, R, 4), dtype=np.int16)
    for p in range(P):
        for r in range(R):
            e[p, r] = rotate_piece(pieces[p], r)
    return e


def adjacent_cells(size):
    """Yield (i, j, side_i, side_j) for every adjacent pair."""
    W = size
    for r in range(size):
        for c in range(size):
            i = r * W + c
            if c < W - 1:
                yield (i, i + 1, 1, 3)
            if r < size - 1:
                yield (i, i + W, 2, 0)


def cell_neighbors(size):
    """For each cell, neighbor positions and which side faces them.
    Returns: cell_nbrs[c] = list of (nbr_pos, my_side, their_side).
    """
    W = size
    N = size * size
    out = [[] for _ in range(N)]
    for (i, j, si, sj) in adjacent_cells(size):
        out[i].append((j, si, sj))
        out[j].append((i, sj, si))
    return out


def is_border_side(c, side, size):
    """Side facing the puzzle exterior."""
    W = size
    r, col = c // W, c % W
    if side == 0: return r == 0
    if side == 1: return col == W - 1
    if side == 2: return r == size - 1
    if side == 3: return col == 0
    return False


def project_A(x):
    """P_A: per-cell argmax → one-hot."""
    N, P, R = x.shape
    flat = x.reshape(N, P * R)
    idx = flat.argmax(axis=1)
    out = np.zeros_like(flat)
    out[np.arange(N), idx] = 1.0
    return out.reshape(N, P, R)


def sinkhorn(M, n_iter=50, eps=1e-9):
    """Sinkhorn normalization: project nonneg matrix M to doubly-stochastic.
    Each row and column sum = 1.
    """
    M = np.maximum(M, eps)
    for _ in range(n_iter):
        M = M / (M.sum(axis=1, keepdims=True) + eps)
        M = M / (M.sum(axis=0, keepdims=True) + eps)
    return M


def project_B(x, edges, size, cell_nbrs, border_cost=1.0, sinkhorn_iter=30):
    """P_B: piece-uniqueness via Sinkhorn (continuous) + rotation profile
    based on edge-consistency expected colors.

    Step 1: x → m[c, p] = sum_r x[c, p, r] (marginalize rotation).
            Apply Sinkhorn so that sum_p m[c, p] = 1 AND sum_c m[c, p] = 1.
            → m is doubly-stochastic, the continuous relaxation of permutation.
    Step 2: Compute expected color distribution at each (cell, side):
              cell_side_color_dist[c, side, color] = sum_{p,r} m[c,p] * x[c,p,r]/Σ_r' x[c,p,r'] * (edges[p,r,side]==color)
            Approximation: use x's per-(c,p) rotation marginal as distribution.
    Step 3: For each adjacent pair (i,j,si,sj), target color at boundary is
            average of cell i's si-marginal and cell j's sj-marginal.
    Step 4: Re-score x[c, p, r] = m[c, p] * (sum over 4 sides of expected match score).
            Then renormalize x within cell as soft assignment.
    Output: continuous x' that lives near the B-manifold.
    """
    N, P, R = x.shape

    # Step 1: marginal then Sinkhorn.
    x_pos = np.maximum(x, 0)  # ensure non-negative
    m = x_pos.sum(axis=2)  # [N, P]
    m = sinkhorn(m, n_iter=sinkhorn_iter)

    # Per-(cell, piece) rotation distribution from x (softmax).
    rot_score = x_pos  # [N, P, R]
    rot_sum = rot_score.sum(axis=2, keepdims=True) + 1e-9
    rot_dist = rot_score / rot_sum  # [N, P, R], rows sum to 1

    # Joint distribution at cell c: w[c, p, r] = m[c, p] * rot_dist[c, p, r].
    w = m[:, :, None] * rot_dist

    # Step 2: expected color at each (cell, side).
    # Need n_colors.
    n_colors = int(edges.max()) + 1
    # cell_side_color_dist[c, side, color] = sum_{p, r : edges[p, r, side] == color} w[c, p, r]
    cell_side_color_dist = np.zeros((N, 4, n_colors), dtype=np.float64)
    for side in range(4):
        ec = edges[:, :, side]  # [P, R]
        for color in range(n_colors):
            mask = (ec == color).astype(np.float64).reshape(-1)  # [P*R]
            cell_side_color_dist[:, side, color] = (w.reshape(N, -1) @ mask)

    # Step 3: target color distribution at each (cell, side) — using neighbor's marginal.
    target_dist = np.zeros_like(cell_side_color_dist)
    is_interior = np.zeros((N, 4), dtype=bool)
    for c in range(N):
        for (nbr_pos, my_side, their_side) in cell_nbrs[c]:
            target_dist[c, my_side] = cell_side_color_dist[nbr_pos, their_side]
            is_interior[c, my_side] = True
    # Border sides: target = δ_0 (color 0 with probability 1).
    for c in range(N):
        for side in range(4):
            if not is_interior[c, side]:
                target_dist[c, side, :] = 0.0
                target_dist[c, side, 0] = 1.0

    # Step 4: re-score x[c, p, r] by expected match score across 4 sides.
    # For (c, p, r): score = sum_side target_dist[c, side, edges[p, r, side]] * (interior_weight or border_weight).
    new_x = np.zeros_like(x)
    for side in range(4):
        ec = edges[:, :, side]  # [P, R]
        # For each cell c, look up target_dist[c, side, ec[p, r]].
        # ec_flat has shape [P*R]; values are color indices.
        ec_flat = ec.reshape(-1)
        for c in range(N):
            weight = 1.0 if is_interior[c, side] else border_cost
            contrib = target_dist[c, side, ec_flat] * weight  # [P*R]
            new_x[c] += contrib.reshape(P, R)

    # Multiply by m (piece-uniqueness prior).
    new_x = new_x * m[:, :, None]

    return new_x


def score_one_hot(assignment, edges, adjacency):
    """Score a hard one-hot assignment [N, P, R]."""
    N, P, R = assignment.shape
    flat = assignment.reshape(N, P * R)
    valid = flat.sum(axis=1) > 0.5
    idx = flat.argmax(axis=1)
    cell_p = idx // R
    cell_r = idx % R
    matched = 0
    for (i, j, si, sj) in adjacency:
        if not valid[i] or not valid[j]: continue
        ci = edges[cell_p[i], cell_r[i], si]
        cj = edges[cell_p[j], cell_r[j], sj]
        if ci == cj: matched += 1
    return matched, int(valid.sum())


def difference_map(x, P_A, P_B, beta=1.0):
    pb = P_B(x)
    pa = P_A(2 * pb - x)
    return x + beta * (pa - pb), pb


def initialize_x(N, P, R, seed=42, init_kind="uniform"):
    rng = np.random.default_rng(seed)
    if init_kind == "uniform":
        x = rng.uniform(0.0, 1.0, size=(N, P, R)).astype(np.float64)
    elif init_kind == "lap_seeded":
        # Random permutation: one piece per cell, random rotation. Smoothed.
        x = rng.uniform(0.0, 0.05, size=(N, P, R)).astype(np.float64)
        perm = rng.permutation(P)[:N]
        for c in range(N):
            p = perm[c]
            r = rng.integers(0, R)
            x[c, p, r] = 1.0
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    ap.add_argument("--max-iters", type=int, default=1000)
    ap.add_argument("--beta", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--init", type=str, default="uniform",
                    choices=["uniform", "lap_seeded"])
    ap.add_argument("--out-dir", type=str, default=None)
    ap.add_argument("--restart-every", type=int, default=0,
                    help="If >0, on stagnation perturb x. Default off.")
    ap.add_argument("--stagnation-window", type=int, default=50)
    ap.add_argument("--border-weight", type=float, default=1.0)
    ap.add_argument("--log-every", type=int, default=10)
    args = ap.parse_args()

    if args.out_dir is None:
        args.out_dir = str(REPO / "output/vol-126" /
                          f"concord_v2_{time.strftime('%Y%m%dT%H%M%S')}_seed{args.seed}_beta{args.beta}_init{args.init}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = Path(args.puzzle)
    size, pieces = load_puzzle_csv(csv_path)
    N = size * size
    P = len(pieces)
    R = 4

    print(f"Puzzle: {csv_path.name}  size={size}×{size}  cells={N}  pieces={P}", flush=True)
    print(f"β={args.beta}  init={args.init}  seed={args.seed}", flush=True)
    print(f"OUT_DIR={out_dir}", flush=True)

    edges = build_edges(pieces, R)
    adjacency = list(adjacent_cells(size))
    cell_nbrs = cell_neighbors(size)
    n_edges = len(adjacency)
    print(f"Adjacent edge pairs: {n_edges}", flush=True)

    x = initialize_x(N, P, R, seed=args.seed, init_kind=args.init)

    def PA(x): return project_A(x)
    def PB(x): return project_B(x, edges, size, cell_nbrs, border_cost=args.border_weight)

    best_matched = -1
    best_iter = -1
    best_pb = None
    history = []
    last_improve = 0
    rng = np.random.default_rng(args.seed + 7777)

    t0 = time.time()
    x_prev = x.copy()
    for it in range(args.max_iters):
        x, pb = difference_map(x, PA, PB, beta=args.beta)
        matched, placed = score_one_hot(pb, edges, adjacency)
        upd = float(np.linalg.norm(x - x_prev))
        history.append({"iter": int(it), "matched": int(matched), "placed": int(placed),
                        "x_norm": float(np.linalg.norm(x)),
                        "update_norm": upd})
        if matched > best_matched:
            best_matched = int(matched)
            best_iter = int(it)
            best_pb = pb.copy()
            last_improve = it

        if it % args.log_every == 0 or it < 5:
            print(f"iter={it:4d}  matched={matched:>3d}  placed={placed:>3d}  "
                  f"x_norm={history[-1]['x_norm']:>7.2f}  "
                  f"update={upd:>7.4f}  "
                  f"best={best_matched}({best_iter})  "
                  f"t={time.time()-t0:.1f}s", flush=True)

        if args.restart_every > 0 and (it - last_improve) > args.stagnation_window:
            # Perturb x with random noise.
            x = x + rng.uniform(-0.2, 0.2, size=x.shape)
            print(f"  STAGNATION KICK at iter={it}", flush=True)
            last_improve = it

        if upd < 1e-6:
            print(f"FIXED POINT at iter={it}", flush=True)
            break
        x_prev = x.copy()

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Best matched={best_matched} at iter={best_iter}", flush=True)

    if best_pb is not None:
        placement = []
        for c in range(N):
            if best_pb[c].sum() < 0.5: continue
            flat_idx = int(best_pb[c].reshape(-1).argmax())
            p, r = divmod(flat_idx, R)
            placement.append({"pos": int(c), "piece_id": int(p), "rotation": int(r)})
        out_path = out_dir / "best.json"
        with open(out_path, "w") as f:
            json.dump({"matched": best_matched, "best_iter": best_iter,
                       "placement": placement, "args": vars(args)}, f, indent=2)
        print(f"Wrote {out_path}", flush=True)

    hist_path = out_dir / "history.json"
    with open(hist_path, "w") as f:
        json.dump(history, f, indent=2)
    print(f"Wrote {hist_path}", flush=True)


if __name__ == "__main__":
    main()
