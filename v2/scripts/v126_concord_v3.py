#!/usr/bin/env python3
"""V126-T1 v3 — CONCORD with Sinkhorn-relaxed P_A and HARD P_B.

State x ∈ R^{N × P × R} (N cells, P pieces, R=4 rotations).

P_A (continuous): per-cell-then-Sinkhorn normalization.
  - Compute m[c, p] = sum_r x[c, p, r].
  - Sinkhorn normalize m (sum_p m[c,p]=1 and sum_c m[c,p]=1).
  - For rotation: softmax over r within each (c, p) at temperature τ.
  - Output: continuous tensor s.t. cell and piece marginals = uniform 1/N each.

P_B (hard): piece-uniqueness LAP + rotation chosen for edge-consistency given
  neighbors' current x argmax.
  - LAP cost = -max_r (edge-agreement score given current neighbors).
  - Output: hard one-hot.

This combination: P_A is continuous (smooths state), P_B is hard (picks the
best discrete assignment from current state). The difference map will move
non-trivially because P_A and P_B's outputs differ when x is in mixed state.

Stability: P_A is a Sinkhorn projection (contractive on the doubly-stochastic
manifold). P_B is a hard projection (idempotent, bounded). Update norm should
stay bounded.
"""

from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment

REPO = Path(__file__).resolve().parents[1]


def load_puzzle_csv(csv_path):
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
    W = size
    for r in range(size):
        for c in range(size):
            i = r * W + c
            if c < W - 1: yield (i, i + 1, 1, 3)
            if r < size - 1: yield (i, i + W, 2, 0)


def cell_neighbors(size):
    N = size * size
    out = [[] for _ in range(N)]
    for (i, j, si, sj) in adjacent_cells(size):
        out[i].append((j, si, sj))
        out[j].append((i, sj, si))
    return out


def sinkhorn(M, n_iter=30, eps=1e-9):
    M = np.maximum(M, eps)
    for _ in range(n_iter):
        M = M / (M.sum(axis=1, keepdims=True) + eps)
        M = M / (M.sum(axis=0, keepdims=True) + eps)
    return M


def project_A(x, sinkhorn_iter=20, tau=1.0):
    """Continuous P_A: Sinkhorn-normalized cell × piece marginal,
    rotation profile = softmax(x[c, p, :] / τ).
    """
    N, P, R = x.shape
    x_pos = np.maximum(x, 0.0)
    m = x_pos.sum(axis=2)
    m = sinkhorn(m, n_iter=sinkhorn_iter)  # [N, P], doubly-stochastic
    # Per-(c, p) rotation softmax.
    rot = x_pos.copy()  # [N, P, R]
    rot = rot - rot.max(axis=2, keepdims=True)
    rot = np.exp(rot / max(tau, 1e-6))
    rot = rot / (rot.sum(axis=2, keepdims=True) + 1e-12)
    return m[:, :, None] * rot


def project_B(x, edges, size, cell_nbrs):
    """Hard P_B: LAP for piece-uniqueness with edge-aware cost.
    1. From x, take argmax per cell as current "committed" choice.
    2. For each (c, p, r), compute edge-agreement score with committed neighbors.
    3. cell_piece_score[c, p] = max_r score[c, p, r].
    4. LAP on -cell_piece_score → piece assignment.
    5. For each (c, p*): rotation = argmax_r score[c, p*, r].
    6. Output one-hot.
    """
    N, P, R = x.shape
    flat = x.reshape(N, P * R)
    cur_idx = flat.argmax(axis=1)
    cur_p = cur_idx // R
    cur_r = cur_idx % R
    cur_colors = np.zeros((N, 4), dtype=np.int16)
    for c in range(N):
        cur_colors[c] = edges[cur_p[c], cur_r[c]]
    nbr_colors = np.zeros((N, 4), dtype=np.int16)
    is_interior = np.zeros((N, 4), dtype=bool)
    for c in range(N):
        for (nbr_pos, my_side, their_side) in cell_nbrs[c]:
            nbr_colors[c, my_side] = cur_colors[nbr_pos, their_side]
            is_interior[c, my_side] = True

    score = np.zeros((N, P, R), dtype=np.float64)
    for side in range(4):
        ec = edges[:, :, side]
        for c in range(N):
            target = nbr_colors[c, side] if is_interior[c, side] else 0
            score[c, :, :] += (ec == target).astype(np.float64)

    cell_piece_score = score.max(axis=2)  # [N, P]
    cost = -cell_piece_score
    row_ind, col_ind = linear_sum_assignment(cost)
    out = np.zeros_like(x)
    for c in range(N):
        p = int(col_ind[c])
        r = int(score[c, p].argmax())
        out[c, p, r] = 1.0
    return out


def score_one_hot(assignment, edges, adjacency):
    N, P, R = assignment.shape
    flat = assignment.reshape(N, P * R)
    valid = flat.sum(axis=1) > 0.5
    idx = flat.argmax(axis=1)
    cell_p = idx // R
    cell_r = idx % R
    matched = 0
    for (i, j, si, sj) in adjacency:
        if not valid[i] or not valid[j]: continue
        if edges[cell_p[i], cell_r[i], si] == edges[cell_p[j], cell_r[j], sj]:
            matched += 1
    return matched, int(valid.sum())


def difference_map(x, P_A, P_B, beta=1.0):
    pb = P_B(x)
    pa = P_A(2 * pb - x)
    return x + beta * (pa - pb), pb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    ap.add_argument("--max-iters", type=int, default=1000)
    ap.add_argument("--beta", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tau", type=float, default=1.0)
    ap.add_argument("--out-dir", type=str, default=None)
    ap.add_argument("--log-every", type=int, default=10)
    args = ap.parse_args()

    if args.out_dir is None:
        args.out_dir = str(REPO / "output/vol-126" /
                          f"concord_v3_{time.strftime('%Y%m%dT%H%M%S')}_s{args.seed}_b{args.beta}_t{args.tau}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = Path(args.puzzle)
    size, pieces = load_puzzle_csv(csv_path)
    N = size * size
    P = len(pieces)
    R = 4
    print(f"Puzzle: {csv_path.name} size={size}×{size} N={N} P={P}", flush=True)
    print(f"β={args.beta} τ={args.tau} seed={args.seed} OUT_DIR={out_dir}", flush=True)

    edges = build_edges(pieces, R)
    adjacency = list(adjacent_cells(size))
    cell_nbrs = cell_neighbors(size)

    rng = np.random.default_rng(args.seed)
    x = rng.uniform(0.0, 1.0, size=(N, P, R)).astype(np.float64)

    def PA(x): return project_A(x, tau=args.tau)
    def PB(x): return project_B(x, edges, size, cell_nbrs)

    best_matched = -1
    best_iter = -1
    best_pb = None
    history = []

    t0 = time.time()
    x_prev = x.copy()
    for it in range(args.max_iters):
        x, pb = difference_map(x, PA, PB, beta=args.beta)
        matched, placed = score_one_hot(pb, edges, adjacency)
        upd = float(np.linalg.norm(x - x_prev))
        xn = float(np.linalg.norm(x))
        history.append({"iter": int(it), "matched": int(matched), "placed": int(placed),
                        "x_norm": xn, "update_norm": upd})
        if matched > best_matched:
            best_matched, best_iter, best_pb = int(matched), int(it), pb.copy()

        if it < 5 or it % args.log_every == 0:
            print(f"iter={it:4d} matched={matched:>4d} placed={placed:>4d} "
                  f"x_norm={xn:>8.2f} upd={upd:>7.4f} best={best_matched}({best_iter}) "
                  f"t={time.time()-t0:.1f}s", flush=True)
        if upd < 1e-6:
            print(f"FIXED POINT iter={it}", flush=True); break
        x_prev = x.copy()

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.1f}s. Best matched={best_matched} at iter={best_iter}", flush=True)

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
    with open(hist_path, "w") as f: json.dump(history, f, indent=2)
    print(f"Wrote {hist_path}", flush=True)


if __name__ == "__main__":
    main()
