#!/usr/bin/env python3
"""Backtracker on canonical E2 using edge-color BP marginals as value order.

This is the natural follow-up to scripts/v12_edge_bp.py: that produced
per-edge marginal distributions (18.84% reduction over uniform), which
is 2.24× the information vol-11's cell-BP achieved. The question is
whether the stronger signal *crosses the threshold* where it actually
helps in a backtracker. Vol-11's measurement was that 8.4% cell-BP
LOST to random; 18.84% edge-BP might be different.

Value-order policy: for each candidate (pid, rot, edges-N,E,S,W) at cell
`pos`, score = sum over the 4 grid-edges incident to `pos` of
`edge_marginal[edge_id][edges[side]]`. Sort descending → try highest-
likelihood values first.

Compare to random and vol-11 cell-BP on identical wall-clock budget.
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from typing import List, Tuple, Optional
import argparse

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v11_load_e2 as loader
import v12_edge_bp as edge_bp

W = H = 16
N = W * H
BORDER = 0
NSTATE = 23


def load_edge_marginals(path: str):
    """Load v12 edge-BP output and return list edges[eid] = np.array(NSTATE)."""
    data = json.load(open(path))
    out = []
    for e in data["edges"]:
        out.append(np.array(e["marginal"]))
    return out, data["info"]


def build_grid_indices():
    """Return cell_to_edge[pos][side] = eid (same as v12_edge_bp)."""
    edges, cell_to_edge, _pinned = edge_bp.build_grid_edges()
    return edges, cell_to_edge


def cell_class(pos):
    x, y = pos % W, pos // W
    n = int(x == 0) + int(x == W - 1) + int(y == 0) + int(y == H - 1)
    if n == 2: return "corner"
    if n == 1: return "edge"
    return "interior"


def piece_class(p):
    n_b = int((p == BORDER).sum())
    if n_b == 2: return "corner"
    if n_b == 1: return "edge"
    return "interior"


def build_domains(pieces, hints):
    """Per-cell domain = [(pid, rot, edges_N,E,S,W)]."""
    hint_at = {pos: (pid, rot) for pos, pid, rot in hints}
    cells = []
    for pos in range(N):
        if pos in hint_at:
            pid, rot = hint_at[pos]
            rotated = tuple(int(c) for c in np.roll(pieces[pid], rot))
            cells.append([(pid, rot, rotated)])
            continue
        cls = cell_class(pos)
        x, y = pos % W, pos // W
        must_border = [y == 0, x == W - 1, y == H - 1, x == 0]
        out = []
        for pid in range(256):
            if piece_class(pieces[pid]) != cls: continue
            for rot in range(4):
                rotated = tuple(int(c) for c in np.roll(pieces[pid], rot))
                ok = True
                for s in range(4):
                    if must_border[s] and rotated[s] != BORDER: ok=False; break
                    if (not must_border[s]) and rotated[s] == BORDER: ok=False; break
                if ok: out.append((pid, rot, rotated))
        cells.append(out)
    return cells


def score_edge_bp(pos, edges_NESW, cell_to_edge, edge_marginals):
    """Sum of edge-marginal at edges_NESW[side] across the 4 sides."""
    s = 0.0
    for side in range(4):
        eid = cell_to_edge[pos][side]
        c = edges_NESW[side]
        s += edge_marginals[eid][c]
    return s


def check_consistent(pos, edges, placed):
    x, y = pos % W, pos // W
    for nx, ny, my_side, nb_side in [(x, y - 1, 0, 2), (x + 1, y, 1, 3),
                                      (x, y + 1, 2, 0), (x - 1, y, 3, 1)]:
        if not (0 <= nx < W and 0 <= ny < H):
            if edges[my_side] != BORDER: return False
            continue
        npos = ny * W + nx
        if placed[npos] is None:
            continue
        _pid, _rot, n_edges = placed[npos]
        if edges[my_side] != n_edges[nb_side]: return False
        if edges[my_side] == BORDER: return False
    return True


def backtrack(puzzle, value_mode, edge_marginals, cell_to_edge, time_budget=60.0, seed=0):
    pieces = puzzle["pieces"]
    domains = build_domains(pieces, puzzle["hints"])
    placed: List[Optional[Tuple[int, int, tuple]]] = [None] * N
    used = np.zeros(256, dtype=bool)
    for pos, pid, rot in puzzle["hints"]:
        rotated = tuple(int(c) for c in np.roll(pieces[pid], rot))
        placed[pos] = (pid, rot, rotated)
        used[pid] = True
    # Pre-sort each domain
    sorted_doms = []
    rng = np.random.default_rng(seed)
    for pos in range(N):
        d = domains[pos]
        if value_mode == "edge_bp":
            d_sorted = sorted(d, key=lambda x: -score_edge_bp(pos, x[2], cell_to_edge, edge_marginals))
        elif value_mode == "random":
            idx = rng.permutation(len(d))
            d_sorted = [d[i] for i in idx]
        else:  # "static"
            d_sorted = list(d)
        sorted_doms.append(d_sorted)

    stats = {"nodes": 0, "backtracks": 0, "max_depth": int(used.sum()),
             "max_score": 0}
    t0 = time.time()

    def score_now():
        m = 0
        for pos in range(N):
            if placed[pos] is None: continue
            x, y = pos % W, pos // W
            _, _, e = placed[pos]
            if x + 1 < W and placed[pos + 1] is not None:
                _, _, ne = placed[pos + 1]
                if e[1] == ne[3] and e[1] != BORDER: m += 1
            if y + 1 < H and placed[pos + W] is not None:
                _, _, ne = placed[pos + W]
                if e[2] == ne[0] and e[2] != BORDER: m += 1
        return m

    # Variable order: border-first MRV (use the count of consistent
    # remaining-candidates as the MRV proxy).
    def select_var():
        best = None; best_key = None
        for pos in range(N):
            if placed[pos] is not None: continue
            cls = cell_class(pos)
            cls_rank = {"corner": 0, "edge": 1, "interior": 2}[cls]
            # count consistent remaining
            d = sorted_doms[pos]
            avail = sum(1 for (p, _, e) in d
                        if not used[p] and check_consistent(pos, e, placed))
            key = (cls_rank, avail, pos)
            if avail == 0: return pos, 0  # forces backtrack
            if best_key is None or key < best_key:
                best_key = key; best = pos
        return best, best_key[1] if best_key else 0

    def dfs():
        stats["nodes"] += 1
        if time.time() - t0 > time_budget:
            return "timeout"
        depth = int(used.sum())
        if depth > stats["max_depth"]:
            stats["max_depth"] = depth
            sc = score_now()
            if sc > stats["max_score"]:
                stats["max_score"] = sc
        if depth == N:
            return "found"
        pos, _ = select_var()
        if pos is None: return "found"
        for (pid, rot, edges) in sorted_doms[pos]:
            if used[pid]: continue
            if not check_consistent(pos, edges, placed): continue
            placed[pos] = (pid, rot, edges)
            used[pid] = True
            res = dfs()
            if res == "found" or res == "timeout":
                return res
            placed[pos] = None
            used[pid] = False
            stats["backtracks"] += 1
        return "exhausted"

    out = dfs()
    elapsed = time.time() - t0
    return stats, elapsed, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--marginals", default="output/v12_bp/edge_bp_60i.json")
    ap.add_argument("--mode", default="edge_bp",
                    choices=["edge_bp", "static", "random"])
    ap.add_argument("--time-budget", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="output/v12_bp/bt_edge_bp.json")
    args = ap.parse_args()

    puzzle = loader.load()
    if args.mode == "edge_bp":
        edge_marginals, info = load_edge_marginals(args.marginals)
        print(f"loaded {len(edge_marginals)} edge marginals from {args.marginals}")
        print(f"  mean_interior_entropy={info['mean_interior_edge_entropy']:.3f} nats "
              f"(reduction {info['interior_reduction_pct']:.2f}%)")
        _edges, cell_to_edge = build_grid_indices()
    else:
        edge_marginals = None
        _edges, cell_to_edge = build_grid_indices()

    print(f"backtracker: mode={args.mode} budget={args.time_budget}s seed={args.seed}")
    stats, elapsed, out = backtrack(puzzle, args.mode, edge_marginals, cell_to_edge,
                                     time_budget=args.time_budget, seed=args.seed)
    print()
    print(f"outcome: {out}")
    print(f"max_depth: {stats['max_depth']}")
    print(f"max_score: {stats['max_score']}")
    print(f"nodes: {stats['nodes']:,}")
    print(f"backtracks: {stats['backtracks']:,}")
    print(f"elapsed: {elapsed:.1f}s")
    print(f"nodes/sec: {stats['nodes']/max(elapsed,1e-6):,.0f}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump({"mode": args.mode, "seed": args.seed,
                   "time_budget": args.time_budget,
                   "stats": stats, "elapsed": elapsed,
                   "outcome": out}, f)
    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
