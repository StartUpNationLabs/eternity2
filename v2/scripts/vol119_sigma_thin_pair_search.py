#!/usr/bin/env python3
"""Vol-119 T3 — σ-thin-pair search.

Vol-118 MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM proved σ-subset
attack is bounded by Δ(S) ≈ -B(S)·p (p ≈ 1.0) where B(S) is the
GRID boundary of subset S. Empirically, our 7-board corpus had B/|S|
~ 1.5× (greedy) and ~1.0× (contiguous, at large k). No cycle had
B/|S| close to the isoperimetric optimum (~0.5×).

OPEN QUESTION (vol-118 MATH_NOTES): "are there σ-cycle PAIRS where
one cycle is nearly contiguous (e.g., a row swap of pieces)? If yes,
that cycle might admit subset lift."

This script answers it for an arbitrary corpus of boards.

For each pair (A, B) and each σ-cycle in their decomposition:
- Compute MIN B(S)/|S| via:
  - exhaustive over 2^N subsets if N ≤ 14
  - random sampling + 1-swap local opt for N > 14
- Report best ratios per pair, per cycle.

A ratio < 1.0 means subset application breaks fewer than |S| boundary
edges; the bound Δ(S) ≈ -B(S) becomes less negative; SUBSET LIFT
might be feasible.

Usage:
    vol119_sigma_thin_pair_search.py board1.json board2.json [board3.json ...]
    vol119_sigma_thin_pair_search.py --glob "output/.../*.json"
"""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

W, H = 16, 16


def load_board(p: Path) -> Tuple[Dict[int, int], Dict[int, int]]:
    """Load board, return (pos→pid, pid→pos)."""
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    pos_to_pid: Dict[int, int] = {}
    pid_to_pos: Dict[int, int] = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        pid = int(item["piece_id"])
        pos_to_pid[pos] = pid
        pid_to_pos[pid] = pos
    return pos_to_pid, pid_to_pos


def sigma_cycles(pos_a: Dict[int, int], pid_b: Dict[int, int]) -> List[List[int]]:
    """Return σ-cycles between A and B as position sequences."""
    s: Dict[int, int] = {}
    for pos, pid in pos_a.items():
        bpos = pid_b.get(pid)
        if bpos is not None and bpos != pos:
            s[pos] = bpos
    visited: set = set()
    cycles: List[List[int]] = []
    for start in s:
        if start in visited:
            continue
        cycle = []
        cur = start
        while cur not in visited and cur in s:
            visited.add(cur)
            cycle.append(cur)
            cur = s[cur]
        if cycle:
            cycles.append(cycle)
    cycles.sort(key=len, reverse=True)
    return cycles


def grid_neighbors(p: int) -> List[int]:
    x, y = p % W, p // W
    out = []
    if x > 0:
        out.append(p - 1)
    if x < W - 1:
        out.append(p + 1)
    if y > 0:
        out.append(p - W)
    if y < H - 1:
        out.append(p + W)
    return out


def boundary(subset: set) -> int:
    """Count (s∈S, n∉S) edges, n on grid (n need not be in cycle)."""
    b = 0
    for p in subset:
        for q in grid_neighbors(p):
            if q not in subset:
                b += 1
    return b


def exhaustive_min_ratio(cycle: List[int]) -> Tuple[float, int, set]:
    """Return (min_ratio, best_k, best_subset) over all proper subsets.

    Bit-encoded enumeration of 2^N. Only safe for N ≤ ~20.
    """
    N = len(cycle)
    if N >= 22:
        raise ValueError(f"exhaustive infeasible for N={N}")
    best_ratio = float('inf')
    best_k = 0
    best_subset = None
    # Use bitmask; skip 0 and (1<<N)-1.
    for mask in range(1, (1 << N) - 1):
        subset = {cycle[i] for i in range(N) if (mask >> i) & 1}
        k = len(subset)
        b = boundary(subset)
        ratio = b / k
        if ratio < best_ratio:
            best_ratio = ratio
            best_k = k
            best_subset = subset
    return best_ratio, best_k, best_subset


def greedy_min_ratio(cycle: List[int], rng: random.Random, max_iters: int = 200) -> Tuple[float, int, set]:
    """Greedy random-restart + 1-swap local opt.

    Strategy:
    1. For each target k ∈ {1, ..., N-1}, do random-restart × T iterations:
       - Start: random k-subset of cycle
       - Local opt: try every (p_in, p_out) swap, accept if strictly improving
    2. Track global-best ratio over all k.
    """
    N = len(cycle)
    best_global = float('inf')
    best_k = 0
    best_subset = None
    cycle_set = set(cycle)

    # Sample k values logarithmically + endpoints
    if N <= 20:
        k_values = list(range(1, N))
    else:
        k_values = sorted(set(
            list(range(1, 11)) +
            [N // 4, N // 2, 3 * N // 4] +
            list(range(N - 10, N))
        ))
        k_values = [k for k in k_values if 1 <= k < N]

    n_restarts = max(3, min(20, max_iters // max(1, len(k_values))))

    for k in k_values:
        for _ in range(n_restarts):
            # Random start
            subset = set(rng.sample(cycle, k))
            cur_b = boundary(subset)
            # Local opt: try all swaps
            improved = True
            local_iters = 0
            max_local = 4 * N
            while improved and local_iters < max_local:
                improved = False
                local_iters += 1
                # Try swapping one IN-element with one OUT-element
                ins = list(subset)
                outs = list(cycle_set - subset)
                rng.shuffle(ins)
                rng.shuffle(outs)
                for p_in in ins:
                    found_better = False
                    for p_out in outs:
                        new_subset = (subset - {p_in}) | {p_out}
                        new_b = boundary(new_subset)
                        if new_b < cur_b:
                            subset = new_subset
                            cur_b = new_b
                            improved = True
                            found_better = True
                            break
                    if found_better:
                        break

            ratio = cur_b / k
            if ratio < best_global:
                best_global = ratio
                best_k = k
                best_subset = subset.copy()

    return best_global, best_k, best_subset


def min_ratio_per_cycle(cycle: List[int], rng: random.Random) -> Tuple[float, int, set]:
    """Dispatch: exhaustive for N ≤ 18, greedy otherwise."""
    N = len(cycle)
    if N <= 18:
        return exhaustive_min_ratio(cycle)
    return greedy_min_ratio(cycle, rng)


def isoperim_lower_bound(k: int) -> float:
    """Isoperimetric lower bound 2·√(π·k) for free k-subsets of the plane."""
    return 2.0 * math.sqrt(math.pi * k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("boards", nargs="*", help="board JSON paths")
    ap.add_argument("--glob", help="glob pattern (alternative to listing boards)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", help="optional output JSON path for full results")
    args = ap.parse_args()

    rng = random.Random(args.seed)

    paths: List[Path] = []
    if args.glob:
        paths.extend(Path(p) for p in glob.glob(args.glob))
    paths.extend(Path(p) for p in args.boards)
    paths = sorted(set(paths))

    if len(paths) < 2:
        print(f"Need ≥2 boards, got {len(paths)}", file=sys.stderr)
        sys.exit(1)

    boards = []
    for p in paths:
        try:
            pos, pid = load_board(p)
            if len(pos) >= 200:  # complete-ish boards only
                boards.append((p, pos, pid))
        except Exception as e:
            print(f"skip {p}: {e}", file=sys.stderr)

    print(f"# vol-119 T3 σ-thin-pair search")
    print(f"# {len(boards)} boards loaded")
    print(f"# pairs: {len(boards) * (len(boards) - 1) // 2}")
    print()

    all_results = []
    overall_min_ratio = float('inf')
    overall_winner = None

    for i in range(len(boards)):
        for j in range(i + 1, len(boards)):
            pa, pos_a, pid_a = boards[i]
            pb, pos_b, pid_b = boards[j]
            cycles = sigma_cycles(pos_a, pid_b)
            if not cycles:
                continue
            sizes = [len(c) for c in cycles]
            total_in_cycles = sum(sizes)
            cycle_results = []
            pair_min_ratio = float('inf')
            pair_min_cycle_idx = -1
            for ci, cycle in enumerate(cycles):
                if len(cycle) < 3:
                    continue
                try:
                    mr, mk, msub = min_ratio_per_cycle(cycle, rng)
                except Exception as e:
                    print(f"cycle skip: {e}", file=sys.stderr)
                    continue
                cycle_results.append({
                    "cycle_idx": ci,
                    "N": len(cycle),
                    "min_ratio": mr,
                    "min_k": mk,
                    "min_B": int(round(mr * mk)),
                    "isoperim_lb": isoperim_lower_bound(mk),
                })
                if mr < pair_min_ratio:
                    pair_min_ratio = mr
                    pair_min_cycle_idx = ci
            print(
                f"pair {pa.name} ↔ {pb.name}: "
                f"{len(cycles)} cycles (sizes {sizes[:5]}{'...' if len(sizes) > 5 else ''}), "
                f"total_cells={total_in_cycles}, "
                f"min_ratio={pair_min_ratio:.3f}"
            )
            all_results.append({
                "pair_a": str(pa),
                "pair_b": str(pb),
                "cycle_sizes": sizes,
                "total_in_cycles": total_in_cycles,
                "cycle_results": cycle_results,
                "pair_min_ratio": pair_min_ratio,
                "pair_min_cycle_idx": pair_min_cycle_idx,
            })
            if pair_min_ratio < overall_min_ratio:
                overall_min_ratio = pair_min_ratio
                overall_winner = (pa, pb, pair_min_cycle_idx)

    print()
    print("# === SUMMARY ===")
    if overall_winner:
        pa, pb, ci = overall_winner
        print(f"# overall MIN B/|S| ratio across all pairs+cycles: {overall_min_ratio:.3f}")
        print(f"# winning pair: {pa.name} ↔ {pb.name}, cycle #{ci}")
    if overall_min_ratio < 1.0:
        print("# (!) min ratio < 1.0 — σ-subset SCORE-LIFT may be feasible")
        print("# (vol-118 MATH_NOTES: Δ(S) ≈ -B(S); ratio < 1 means partial gain possible)")
    else:
        print("# min ratio ≥ 1.0 — σ-subset attack remains bounded by vol-118 theorem")

    if args.out:
        with open(args.out, "w") as f:
            json.dump({
                "boards": [str(p) for p, _, _ in boards],
                "results": all_results,
                "overall_min_ratio": overall_min_ratio,
            }, f, indent=2)
        print(f"# wrote: {args.out}")


if __name__ == "__main__":
    main()
