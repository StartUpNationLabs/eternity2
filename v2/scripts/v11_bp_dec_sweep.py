#!/usr/bin/env python3
"""Run BP-decimation with one configuration. Designed for the parallel
launcher to invoke 8 of these in parallel with different args.

Usage: v11_bp_dec_sweep.py <damping> <batch_size> <m_parisi> <seed> <out_path>
"""
from __future__ import annotations

import sys
import time
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Set

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load, rotate_edges
from v11_factor_graph import build_domains, adjacency_pairs, cell_class, SIZE, N
from v11_bp_uniq import piece_availability
from v11_bp import EPS
from v11_sp import sp_iteration, compute_beliefs_sp


def fresh_messages_for_domains(domains, pairs):
    m_var2fac = {}
    for pair_idx, (a, b, side_ab) in enumerate(pairs):
        m_var2fac[(pair_idx, 0)] = np.full(max(1, len(domains[a])), 1.0 / max(1, len(domains[a])))
        m_var2fac[(pair_idx, 1)] = np.full(max(1, len(domains[b])), 1.0 / max(1, len(domains[b])))
    return m_var2fac


def build_cell_to_pairs(domains, pairs):
    cell_to_pairs: List[List[Tuple[int, int, int, int]]] = [[] for _ in range(N)]
    for pair_idx, (a, b, side_ab) in enumerate(pairs):
        cell_to_pairs[a].append((pair_idx, 0, side_ab, b))
        cell_to_pairs[b].append((pair_idx, 1, (side_ab + 2) % 4, a))
    return cell_to_pairs


def precompute(domains, pieces):
    edges_per_cell = []
    pids_per_cell = []
    for pos in range(N):
        D = domains[pos]
        n = len(D)
        E = np.zeros((n, 4), dtype=np.int8)
        P = np.zeros(n, dtype=np.int16)
        for i, (pid, rot) in enumerate(D):
            E[i, :] = rotate_edges(pieces[pid], rot)
            P[i] = pid
        edges_per_cell.append(E)
        pids_per_cell.append(P)
    return edges_per_cell, pids_per_cell


def cell_entropies(beliefs):
    H = np.zeros(N, dtype=np.float64)
    for pos, b in enumerate(beliefs):
        bb = np.clip(b, EPS, 1.0)
        H[pos] = -np.sum(bb * np.log(bb))
    return H


def propagate_after_fix(fixed_pos, pid, rot, placements, domains, pieces):
    touched: Set[int] = set()
    for pos in range(N):
        if pos == fixed_pos or pos in placements:
            continue
        new_D = [(p, r) for p, r in domains[pos] if p != pid]
        if len(new_D) != len(domains[pos]):
            touched.add(pos)
            domains[pos] = new_D
            if not new_D:
                return False, touched
    fixed_edges = rotate_edges(pieces[pid], rot)
    x, y = fixed_pos % SIZE, fixed_pos // SIZE
    for (nx, ny, my_side, nb_side) in [
        (x, y - 1, 0, 2),
        (x + 1, y, 1, 3),
        (x, y + 1, 2, 0),
        (x - 1, y, 3, 1),
    ]:
        if not (0 <= nx < SIZE and 0 <= ny < SIZE):
            continue
        npos = ny * SIZE + nx
        if npos in placements:
            continue
        req = int(fixed_edges[my_side])
        new_D = []
        for (p, r) in domains[npos]:
            e = rotate_edges(pieces[p], r)
            if e[nb_side] == req:
                new_D.append((p, r))
        if len(new_D) != len(domains[npos]):
            touched.add(npos)
            domains[npos] = new_D
            if not new_D:
                return False, touched
    return True, touched


def rebuild_cell_arrays_for(touched, domains, edges_per_cell, pids_per_cell, pieces):
    for pos in touched:
        D = domains[pos]
        n = len(D)
        E = np.zeros((n, 4), dtype=np.int8)
        P = np.zeros(n, dtype=np.int16)
        for i, (pid, rot) in enumerate(D):
            E[i, :] = rotate_edges(pieces[pid], rot)
            P[i] = pid
        edges_per_cell[pos] = E
        pids_per_cell[pos] = P


def compute_score(placements, pieces) -> int:
    matched = 0
    placement_edges = {}
    for pos, (pid, rot) in placements.items():
        placement_edges[pos] = rotate_edges(pieces[pid], rot)
    for pos, edges in placement_edges.items():
        x, y = pos % SIZE, pos // SIZE
        if x + 1 < SIZE and (pos + 1) in placement_edges:
            if edges[1] == placement_edges[pos + 1][3] and edges[1] != 0:
                matched += 1
        if y + 1 < SIZE and (pos + SIZE) in placement_edges:
            if edges[2] == placement_edges[pos + SIZE][0] and edges[2] != 0:
                matched += 1
    return matched


def run(damping, batch_size, m_parisi, seed, out_path):
    random.seed(seed)
    np.random.seed(seed)

    puzzle = load()
    pieces = puzzle["pieces"]
    domains = build_domains(puzzle)
    edges_per_cell, pids_per_cell = precompute(domains, pieces)
    pairs = adjacency_pairs()
    m_var2fac = fresh_messages_for_domains(domains, pairs)
    cell_to_pairs = build_cell_to_pairs(domains, pairs)
    avail = np.ones(256, dtype=np.float64)
    placements: Dict[int, Tuple[int, int]] = {(pos): (pid, rot) for pos, pid, rot in puzzle["hints"]}

    log = []
    t0 = time.time()
    contradiction = False
    round_idx = 0
    max_depth_reached = len(placements)
    best_score = compute_score(placements, pieces)

    while len(placements) < N and not contradiction:
        round_idx += 1
        for it in range(50):
            change = sp_iteration(domains, edges_per_cell, pids_per_cell,
                                  pairs, m_var2fac, cell_to_pairs, avail,
                                  m_parisi=m_parisi, damping=damping)
            if change < 1e-3:
                break
        beliefs = compute_beliefs_sp(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail, m_parisi=m_parisi
        )
        avail = 0.5 * avail + 0.5 * piece_availability(beliefs, pids_per_cell)
        for it in range(15):
            change = sp_iteration(domains, edges_per_cell, pids_per_cell,
                                  pairs, m_var2fac, cell_to_pairs, avail,
                                  m_parisi=m_parisi, damping=damping)
            if change < 1e-3:
                break
        beliefs = compute_beliefs_sp(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail, m_parisi=m_parisi
        )
        H = cell_entropies(beliefs)

        # Cascade-fix
        cascades = []
        for pos in range(N):
            if pos in placements:
                continue
            if len(domains[pos]) == 0:
                contradiction = True
                log.append({"event": "empty_domain", "pos": pos, "depth": len(placements)})
                break
            if len(domains[pos]) == 1:
                pid, rot = domains[pos][0]
                cascades.append((pos, pid, rot))
        if contradiction:
            break

        for pos, pid, rot in cascades:
            if pos in placements:
                continue
            placements[pos] = (pid, rot)
            ok, touched = propagate_after_fix(pos, pid, rot, placements, domains, pieces)
            if not ok:
                contradiction = True
                log.append({"event": "propagation_empty_cascade", "pos": pos,
                            "depth": len(placements)})
                break
            rebuild_cell_arrays_for(touched, domains, edges_per_cell, pids_per_cell, pieces)
        if contradiction:
            break
        if cascades:
            m_var2fac = fresh_messages_for_domains(domains, pairs)
            cell_to_pairs = build_cell_to_pairs(domains, pairs)
            avail = np.ones(256, dtype=np.float64)
            best_score = max(best_score, compute_score(placements, pieces))
            max_depth_reached = max(max_depth_reached, len(placements))
            continue

        candidates = sorted(
            ((H[p], p) for p in range(N)
             if p not in placements and len(domains[p]) >= 2),
            key=lambda x: (x[0], random.random()),  # entropy + seeded tiebreak
        )
        if not candidates:
            break
        fixed_this_round = []
        excluded: Set[int] = set()
        for h, pos in candidates:
            if len(fixed_this_round) >= batch_size:
                break
            if pos in excluded:
                continue
            b = beliefs[pos]
            s_idx = int(np.argmax(b))
            pid, rot = domains[pos][s_idx]
            already_picked_pids = {p for (_, p, _) in fixed_this_round}
            if pid in already_picked_pids:
                ranked = np.argsort(-b)
                picked = False
                for alt in ranked:
                    alt_pid, alt_rot = domains[pos][alt]
                    if alt_pid not in already_picked_pids:
                        s_idx = int(alt)
                        pid, rot = alt_pid, alt_rot
                        picked = True
                        break
                if not picked:
                    continue
            fixed_this_round.append((pos, pid, rot))
            x, y = pos % SIZE, pos // SIZE
            for (nx, ny) in [(x, y-1), (x+1, y), (x, y+1), (x-1, y)]:
                if 0 <= nx < SIZE and 0 <= ny < SIZE:
                    excluded.add(ny * SIZE + nx)
            excluded.add(pos)
        for pos, pid, rot in fixed_this_round:
            placements[pos] = (pid, rot)
            ok, touched = propagate_after_fix(pos, pid, rot, placements, domains, pieces)
            if not ok:
                contradiction = True
                log.append({"event": "propagation_empty_in_batch", "pos": pos,
                            "depth": len(placements)})
                break
            rebuild_cell_arrays_for(touched, domains, edges_per_cell, pids_per_cell, pieces)
            log.append({"event": "fix", "pos": pos, "pid": pid, "rot": rot,
                        "H_before": float(H[pos]), "depth": len(placements),
                        "t": time.time() - t0})
        max_depth_reached = max(max_depth_reached, len(placements))
        best_score = max(best_score, compute_score(placements, pieces))
        if contradiction:
            break
        m_var2fac = fresh_messages_for_domains(domains, pairs)
        cell_to_pairs = build_cell_to_pairs(domains, pairs)

    elapsed = time.time() - t0
    final_score = compute_score(placements, pieces)
    out = {
        "config": {"damping": damping, "batch_size": batch_size,
                   "m_parisi": m_parisi, "seed": seed},
        "max_depth_reached": max_depth_reached,
        "final_depth": len(placements),
        "best_score": int(best_score),
        "final_score": int(final_score),
        "contradiction": contradiction,
        "wall_clock_s": elapsed,
        "n_log_events": len(log),
        "log_tail": log[-20:],
        "placements": [[int(pos), int(pid), int(rot)] for pos, (pid, rot) in placements.items()],
    }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[{seed}] damping={damping} batch={batch_size} m={m_parisi}: "
          f"depth={max_depth_reached} score={best_score} contradiction={contradiction} t={elapsed:.1f}s")


def main():
    args = sys.argv[1:]
    if len(args) != 5:
        print("usage: damping batch_size m_parisi seed out_path", file=sys.stderr)
        sys.exit(1)
    damping = float(args[0])
    batch_size = int(args[1])
    m_parisi = float(args[2])
    seed = int(args[3])
    out_path = args[4]
    run(damping, batch_size, m_parisi, seed, out_path)


if __name__ == "__main__":
    main()
