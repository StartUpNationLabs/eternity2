#!/usr/bin/env python3
"""SP-decimation + chronological backtrack hybrid (v2, simplified).

Winning config from sweep 6: SP m=0.30 / batch=1 / damping=0.3
reached depth 125 / score 211. We augment with chronological
backtracking: on contradiction (or after exhausting top-K values
at a cell), roll back rollback_depth fixes and try the next value
at the rolled-back cell.

Implementation note: after every domain mutation we re-init the
message arrays from scratch (cheap, ~25 ms for full graph).
"""
from __future__ import annotations

import sys
import time
import json
import argparse
import random
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load, rotate_edges
from v11_factor_graph import build_domains, adjacency_pairs, cell_class, SIZE, N
from v11_bp_uniq import piece_availability
from v11_bp import EPS
from v11_sp import sp_iteration, compute_beliefs_sp


def fresh_messages(domains, pairs):
    m = {}
    for pi, (a, b, s) in enumerate(pairs):
        m[(pi, 0)] = np.full(max(1, len(domains[a])), 1.0 / max(1, len(domains[a])))
        m[(pi, 1)] = np.full(max(1, len(domains[b])), 1.0 / max(1, len(domains[b])))
    return m


def build_c2p(domains, pairs):
    c2p: List[List] = [[] for _ in range(N)]
    for pi, (a, b, s) in enumerate(pairs):
        c2p[a].append((pi, 0, s, b))
        c2p[b].append((pi, 1, (s + 2) % 4, a))
    return c2p


def precompute(domains, pieces):
    epc = []; ppc = []
    for pos in range(N):
        D = domains[pos]; n = len(D)
        E = np.zeros((n, 4), dtype=np.int8); P = np.zeros(n, dtype=np.int16)
        for i, (pid, rot) in enumerate(D):
            E[i, :] = rotate_edges(pieces[pid], rot); P[i] = pid
        epc.append(E); ppc.append(P)
    return epc, ppc


def cell_entropies(beliefs):
    H = np.zeros(N)
    for pos, b in enumerate(beliefs):
        bb = np.clip(b, EPS, 1.0)
        H[pos] = -np.sum(bb * np.log(bb))
    return H


def propagate_after_fix(pos, pid, rot, placements, domains, pieces):
    """Returns (ok, touched_dict) where touched_dict[pos] = old_domain."""
    touched = {}
    fixed_edges = rotate_edges(pieces[pid], rot)
    for opos in range(N):
        if opos == pos or opos in placements:
            continue
        old = domains[opos]
        new_D = [(p, r) for p, r in old if p != pid]
        if len(new_D) != len(old):
            touched[opos] = old
            domains[opos] = new_D
            if not new_D:
                return False, touched
    x, y = pos % SIZE, pos // SIZE
    for (nx, ny, my_side, nb_side) in [(x,y-1,0,2),(x+1,y,1,3),(x,y+1,2,0),(x-1,y,3,1)]:
        if not (0 <= nx < SIZE and 0 <= ny < SIZE): continue
        npos = ny * SIZE + nx
        if npos in placements: continue
        req = int(fixed_edges[my_side])
        old = domains[npos]
        new_D = []
        for (p, r) in old:
            e = rotate_edges(pieces[p], r)
            if e[nb_side] == req:
                new_D.append((p, r))
        if len(new_D) != len(old):
            if npos not in touched:
                touched[npos] = old
            domains[npos] = new_D
            if not new_D:
                return False, touched
    return True, touched


def compute_score(placements, pieces) -> int:
    matched = 0
    pe = {}
    for pos, (pid, rot) in placements.items():
        pe[pos] = rotate_edges(pieces[pid], rot)
    for pos, edges in pe.items():
        x, y = pos % SIZE, pos // SIZE
        if x + 1 < SIZE and (pos + 1) in pe:
            if edges[1] == pe[pos + 1][3] and edges[1] != 0: matched += 1
        if y + 1 < SIZE and (pos + SIZE) in pe:
            if edges[2] == pe[pos + SIZE][0] and edges[2] != 0: matched += 1
    return matched


def initial_state(puzzle):
    pieces = puzzle["pieces"]
    domains = build_domains(puzzle)
    placements = {pos: (pid, rot) for pos, pid, rot in puzzle["hints"]}
    # Propagate hints
    for hpos, hpid, hrot in puzzle["hints"]:
        for opos in range(N):
            if opos == hpos or opos in placements:
                continue
            domains[opos] = [(p, r) for p, r in domains[opos] if p != hpid]
        edges = rotate_edges(pieces[hpid], hrot)
        x, y = hpos % SIZE, hpos // SIZE
        for (nx, ny, my_side, nb_side) in [(x,y-1,0,2),(x+1,y,1,3),(x,y+1,2,0),(x-1,y,3,1)]:
            if not (0 <= nx < SIZE and 0 <= ny < SIZE): continue
            npos = ny * SIZE + nx
            if npos in placements: continue
            req = int(edges[my_side])
            new_D = []
            for (p, r) in domains[npos]:
                e = rotate_edges(pieces[p], r)
                if e[nb_side] == req:
                    new_D.append((p, r))
            domains[npos] = new_D
    return placements, domains


def run(damping, m_parisi, rollback_depth, time_budget, seed, out_path):
    random.seed(seed); np.random.seed(seed)
    puzzle = load(); pieces = puzzle["pieces"]
    placements, domains = initial_state(puzzle)
    pairs = adjacency_pairs()

    # Decimation history: stack of (pos, snapshot_touched_domains, fix_idx,
    # ranked_states)
    history: List[Tuple[int, Dict[int, List[Tuple[int, int]]], int, List[Tuple[int, int]]]] = []
    best_depth = len(placements)
    best_score = compute_score(placements, pieces)
    t0 = time.time()
    n_fixes = 0; n_backtracks = 0
    log_summary = []
    max_try_per_cell = 6
    summary_print_interval = 25

    while len(placements) < N:
        if time.time() - t0 > time_budget:
            break
        # Rebuild precomputes and messages from current domain state
        edges_per_cell, pids_per_cell = precompute(domains, pieces)
        m_var2fac = fresh_messages(domains, pairs)
        c2p = build_c2p(domains, pairs)
        avail = np.ones(256, dtype=np.float64)

        # SP to convergence
        for it in range(40):
            ch = sp_iteration(domains, edges_per_cell, pids_per_cell, pairs,
                              m_var2fac, c2p, avail, m_parisi=m_parisi,
                              damping=damping)
            if ch < 1e-3: break
        beliefs = compute_beliefs_sp(domains, edges_per_cell, pids_per_cell,
                                     pairs, m_var2fac, c2p, avail,
                                     m_parisi=m_parisi)
        avail = 0.5 * avail + 0.5 * piece_availability(beliefs, pids_per_cell)
        for it in range(8):
            ch = sp_iteration(domains, edges_per_cell, pids_per_cell, pairs,
                              m_var2fac, c2p, avail, m_parisi=m_parisi,
                              damping=damping)
            if ch < 1e-3: break
        beliefs = compute_beliefs_sp(domains, edges_per_cell, pids_per_cell,
                                     pairs, m_var2fac, c2p, avail,
                                     m_parisi=m_parisi)
        H = cell_entropies(beliefs)

        # Empty-domain check first
        empty_pos = -1
        for pos in range(N):
            if pos in placements: continue
            if len(domains[pos]) == 0:
                empty_pos = pos; break
        if empty_pos >= 0:
            # Trigger backtrack
            n_backtracks += 1
            if not history: break
            for _ in range(rollback_depth):
                if not history: break
                pos, touched, fix_idx, ranked = history.pop()
                del placements[pos]
                for tpos, told in touched.items():
                    domains[tpos] = told
            continue

        # Pick lowest-H non-placed cell
        best_pos = -1; best_h = float("inf")
        for pos in range(N):
            if pos in placements: continue
            if H[pos] < best_h:
                best_h = H[pos]; best_pos = pos
        if best_pos < 0: break

        b = beliefs[best_pos]
        D = domains[best_pos]
        ranked = [D[i] for i in np.argsort(-b)]

        fixed_this_round = False
        for fix_idx, (pid, rot) in enumerate(ranked[:max_try_per_cell]):
            placements[best_pos] = (pid, rot)
            ok, touched = propagate_after_fix(best_pos, pid, rot, placements,
                                              domains, pieces)
            if ok:
                history.append((best_pos, touched, fix_idx, ranked))
                n_fixes += 1
                d = len(placements)
                sc = compute_score(placements, pieces)
                if d > best_depth:
                    best_depth = d
                    log_summary.append({"event": "new_best_depth", "depth": d,
                                        "score": sc, "t": time.time() - t0,
                                        "fix_idx": fix_idx, "pos": best_pos,
                                        "pid": pid, "rot": rot})
                if sc > best_score:
                    best_score = sc
                fixed_this_round = True
                break
            else:
                # Undo this attempt
                for tpos, told in touched.items():
                    domains[tpos] = told
                del placements[best_pos]

        if not fixed_this_round:
            # All top-K alternatives failed at this cell — backtrack
            n_backtracks += 1
            if not history: break
            for _ in range(rollback_depth):
                if not history: break
                pos, touched, fix_idx, ranked2 = history.pop()
                del placements[pos]
                for tpos, told in touched.items():
                    domains[tpos] = told

        if n_fixes > 0 and n_fixes % summary_print_interval == 0:
            elapsed = time.time() - t0
            sc = compute_score(placements, pieces)
            print(f"  fixes={n_fixes} depth={len(placements)}/256 "
                  f"score={sc}/480 best_score={best_score} bt={n_backtracks} "
                  f"t={elapsed:.1f}s", flush=True)

    elapsed = time.time() - t0
    out = {
        "config": {"damping": damping, "m_parisi": m_parisi,
                   "rollback_depth": rollback_depth,
                   "time_budget_s": time_budget, "seed": seed},
        "best_depth": best_depth,
        "best_score": int(best_score),
        "n_fixes": n_fixes,
        "n_backtracks": n_backtracks,
        "final_depth": len(placements),
        "wall_clock_s": elapsed,
        "log": log_summary,
        "placements": [[int(pos), int(pid), int(rot)] for pos, (pid, rot) in placements.items()],
    }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[{seed}] damp={damping} m={m_parisi} rb={rollback_depth}: "
          f"best_depth={best_depth} best_score={best_score} "
          f"backtracks={n_backtracks} t={elapsed:.1f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--damping", type=float, default=0.3)
    ap.add_argument("--m-parisi", type=float, default=0.3)
    ap.add_argument("--rollback-depth", type=int, default=10)
    ap.add_argument("--time-budget", type=float, default=300.0)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default=str(ROOT / "output" / "v11_sp" / "sp_backtrack_hybrid.json"))
    args = ap.parse_args()
    run(args.damping, args.m_parisi, args.rollback_depth, args.time_budget,
        args.seed, args.out)


if __name__ == "__main__":
    main()
