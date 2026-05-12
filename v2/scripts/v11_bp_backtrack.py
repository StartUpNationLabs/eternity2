#!/usr/bin/env python3
"""BP-marginal-guided backtracker on E2.

Architecture: offline BP-with-uniqueness has computed per-cell state
marginals (from hint-only state). We use those marginals to drive a
classical CSP backtracker:

- Variable order: pick UNPLACED cell with smallest current domain
  (MRV — minimum-remaining-values). Tie-break by BP entropy: cell with
  lower BP entropy has stronger evidence, branch there first.
- Value order: for each domain row at the chosen cell, sort by the BP
  marginal probability of that (piece_id, rotation) at that cell.

Backtracker is chronological, with forward checking on neighbor edges
and piece-uniqueness. The goal isn't to solve E2 (which would take
years at any tractable node rate); it's to measure whether BP-guided
heuristics make the backtracker find higher partial scores faster
than the baseline (LCV / no marginals).

Wall-clock budget: short (e.g., 60s). Report depth reached, score,
backtrack count, nodes visited.
"""
from __future__ import annotations

import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load, rotate_edges
from v11_factor_graph import build_domains, cell_class, SIZE, N

MARGINALS_PATH = ROOT / "output" / "v11_sp" / "bp_marginals.json"


def load_marginals() -> Tuple[Dict[Tuple[int, int, int], float], np.ndarray]:
    """Return (marginal_lookup[(pos, pid, rot)] -> p, entropy[pos])."""
    with MARGINALS_PATH.open() as f:
        data = json.load(f)
    H = np.zeros(N, dtype=np.float64)
    lookup: Dict[Tuple[int, int, int], float] = {}
    for cell in data["marginals"]:
        pos = cell["pos"]
        H[pos] = cell["entropy"]
        for s in cell["states"]:
            lookup[(pos, s["piece_id"], s["rotation"])] = s["marginal"]
    return lookup, H


def order_value(domain, pos, marg_lookup, mode):
    if mode == "bp":
        # Sort by BP marginal descending
        return sorted(domain, key=lambda x: -marg_lookup.get((pos, x[0], x[1]), 0.0))
    if mode == "random":
        import random
        d = list(domain)
        random.shuffle(d)
        return d
    return list(domain)


def choose_var(domains, placed, used, H, mode, prefer_border=True):
    """Pick the next variable to branch on.

    Strategy:
      MRV first (smallest domain).
      Tiebreak: prefer border cells (corners > edges > interior) if prefer_border.
      Tiebreak: lowest BP entropy.
    """
    best = -1
    best_key = None
    for pos in range(N):
        if placed[pos] is not None:
            continue
        D = domains[pos]
        if not D:
            return -2  # contradiction
        if len(D) == 1:
            return pos  # singleton — always pick
        cls = cell_class(pos)
        cls_rank = {"corner": 0, "edge": 1, "interior": 2}[cls]
        key = (len(D), cls_rank if prefer_border else 0, H[pos])
        if best_key is None or key < best_key:
            best_key = key
            best = pos
    return best


def check_consistent(pos, pid, rot, placed, pieces) -> bool:
    """Edge-equality against already-placed neighbors."""
    edges = rotate_edges(pieces[pid], rot)
    x, y = pos % SIZE, pos // SIZE
    for (nx, ny, my_side, nb_side) in [
        (x, y - 1, 0, 2), (x + 1, y, 1, 3), (x, y + 1, 2, 0), (x - 1, y, 3, 1)
    ]:
        if not (0 <= nx < SIZE and 0 <= ny < SIZE):
            # frame; my edge on this side must be BORDER (0)
            if edges[my_side] != 0:
                return False
            continue
        npos = ny * SIZE + nx
        if placed[npos] is None:
            continue
        nb_pid, nb_rot = placed[npos]
        nb_edges = rotate_edges(pieces[nb_pid], nb_rot)
        if edges[my_side] != nb_edges[nb_side]:
            return False
        # Border check: any non-frame neighbor must not show BORDER toward us
        if edges[my_side] == 0:
            return False
    return True


def filter_domain(pos, domain, placed, pieces) -> List[Tuple[int, int]]:
    """Prune `domain` to only states consistent with all already-placed neighbors."""
    return [(p, r) for (p, r) in domain if check_consistent(pos, p, r, placed, pieces)]


def backtrack(puzzle, marg_lookup, H, value_mode="bp", time_budget=60.0):
    pieces = puzzle["pieces"]
    domains = build_domains(puzzle)
    # Apply hints
    placed: List[Tuple[int, int] | None] = [None] * N
    used = np.zeros(256, dtype=bool)
    for pos, pid, rot in puzzle["hints"]:
        placed[pos] = (pid, rot)
        used[pid] = True
        domains[pos] = [(pid, rot)]
    # After hint placement, propagate piece-uniqueness once and neighbor pruning.
    for pos in range(N):
        if placed[pos] is None:
            domains[pos] = [(p, r) for p, r in domains[pos] if not used[p]]
            domains[pos] = filter_domain(pos, domains[pos], placed, pieces)

    stats = {"nodes": 0, "backtracks": 0, "max_depth": int(used.sum()),
             "max_score": 0, "trial_count": 0}
    t0 = time.time()
    timed_out = [False]

    # Pre-sort each domain by BP marginal once. Use a frozen copy.
    sorted_domains: List[List[Tuple[int, int]]] = []
    for pos in range(N):
        if placed[pos] is not None:
            sorted_domains.append([placed[pos]])
        else:
            sorted_domains.append(order_value(domains[pos], pos, marg_lookup, value_mode))

    def score_now() -> int:
        m = 0
        for pos in range(N):
            if placed[pos] is None:
                continue
            x, y = pos % SIZE, pos // SIZE
            pid, rot = placed[pos]
            edges = rotate_edges(pieces[pid], rot)
            if x + 1 < SIZE and placed[pos + 1] is not None:
                npid, nrot = placed[pos + 1]
                nedges = rotate_edges(pieces[npid], nrot)
                if edges[1] == nedges[3] and edges[1] != 0:
                    m += 1
            if y + 1 < SIZE and placed[pos + SIZE] is not None:
                npid, nrot = placed[pos + SIZE]
                nedges = rotate_edges(pieces[npid], nrot)
                if edges[2] == nedges[0] and edges[2] != 0:
                    m += 1
        return m

    def search(depth):
        if time.time() - t0 > time_budget:
            timed_out[0] = True
            return False
        stats["nodes"] += 1

        if depth == N:
            return True

        # Pick next variable
        pos = choose_var(domains, placed, used, H, value_mode)
        if pos == -2:
            return False
        if pos == -1:
            return False

        # Try values
        D = domains[pos]
        # Always re-sort by current marginal (which is static here; we
        # use the pre-sorted snapshot).
        # Filter by piece-uniqueness AND edge consistency.
        candidates = order_value(D, pos, marg_lookup, value_mode)
        for (pid, rot) in candidates:
            if used[pid]:
                continue
            if not check_consistent(pos, pid, rot, placed, pieces):
                continue
            # Tentative place
            placed[pos] = (pid, rot)
            used[pid] = True
            stats["trial_count"] += 1
            # Forward checking: prune neighbor domains
            x, y = pos % SIZE, pos // SIZE
            saved = {}
            ok = True
            edges = rotate_edges(pieces[pid], rot)
            for (nx, ny, my_side, nb_side) in [
                (x, y-1, 0, 2), (x+1, y, 1, 3), (x, y+1, 2, 0), (x-1, y, 3, 1)
            ]:
                if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                    continue
                npos = ny * SIZE + nx
                if placed[npos] is not None:
                    continue
                req = int(edges[my_side])
                new_D = []
                for (p, r) in domains[npos]:
                    if p == pid:
                        continue
                    if used[p]:
                        continue
                    e = rotate_edges(pieces[p], r)
                    if e[nb_side] == req:
                        new_D.append((p, r))
                if not new_D:
                    ok = False
                saved[npos] = domains[npos]
                domains[npos] = new_D
                if not ok:
                    break
            # Also prune the chosen piece from ALL other unplaced cells.
            # (This is the piece-uniqueness forward check.)
            saved_uniq = {}
            if ok:
                for opos in range(N):
                    if opos == pos or placed[opos] is not None:
                        continue
                    new_D = [(p, r) for p, r in domains[opos] if p != pid]
                    if len(new_D) != len(domains[opos]):
                        saved_uniq[opos] = domains[opos]
                        domains[opos] = new_D
                        if not new_D:
                            ok = False
                            break
            if ok:
                # Score & depth tracking
                d = sum(1 for p in placed if p is not None)
                if d > stats["max_depth"]:
                    stats["max_depth"] = d
                    sc = score_now()
                    if sc > stats["max_score"]:
                        stats["max_score"] = sc
                if search(depth + 1):
                    return True
            # Undo
            for npos_, D_ in saved.items():
                domains[npos_] = D_
            for opos_, D_ in saved_uniq.items():
                domains[opos_] = D_
            placed[pos] = None
            used[pid] = False
            stats["backtracks"] += 1
        return False

    search(int(used.sum()))
    elapsed = time.time() - t0
    return stats, elapsed, placed, timed_out[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--value-mode", default="bp", choices=["bp", "static", "random"])
    ap.add_argument("--time-budget", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=str(ROOT / "output" / "v11_sp" / "bp_backtrack.json"))
    args = ap.parse_args()
    import random
    random.seed(args.seed)
    np.random.seed(args.seed)

    print(f"Loading BP marginals from {MARGINALS_PATH.relative_to(ROOT)}...")
    marg_lookup, H = load_marginals()
    print(f"Loaded {len(marg_lookup)} state marginals. mean_H={H.mean():.3f}")

    puzzle = load()
    print(f"E2 backtracker (value_mode={args.value_mode}, budget={args.time_budget:.0f}s)")
    print()
    stats, elapsed, placed, timed_out = backtrack(puzzle, marg_lookup, H,
                                                   value_mode=args.value_mode,
                                                   time_budget=args.time_budget)
    print(f"\n=== Result (value_mode={args.value_mode}) ===")
    print(f"max_depth_reached: {stats['max_depth']}/256")
    print(f"max_score_reached: {stats['max_score']}/480")
    print(f"nodes:             {stats['nodes']}")
    print(f"backtracks:        {stats['backtracks']}")
    print(f"trial_count:       {stats['trial_count']}")
    print(f"elapsed:           {elapsed:.1f}s")
    print(f"timed_out:         {timed_out}")

    out = {
        "value_mode": args.value_mode,
        "time_budget_s": args.time_budget,
        "stats": stats,
        "elapsed_s": elapsed,
        "timed_out": timed_out,
        "n_placed": sum(1 for p in placed if p is not None),
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
