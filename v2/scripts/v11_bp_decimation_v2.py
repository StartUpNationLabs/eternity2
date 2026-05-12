#!/usr/bin/env python3
"""BP-decimation v2: batched, warm-started, instrumented.

Improvements over v1:
- Warm-start BP from previous messages (only re-init touched cells).
- Fix top-K lowest-entropy cells per round (default K=16).
- Print progress every batch.
- Save the placement trajectory.
- Stop on contradiction with a clear log.
"""
from __future__ import annotations

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load, rotate_edges
from v11_factor_graph import build_domains, adjacency_pairs, cell_class, SIZE, N
from v11_bp_uniq import (
    bp_iteration_with_uniqueness, compute_beliefs_with_uniqueness,
    piece_availability
)
from v11_bp import precompute_state_info, cell_entropies, EPS


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


def propagate_after_fix(
    fixed_pos: int, pid: int, rot: int,
    placements: Dict[int, Tuple[int, int]],
    domains: List[List[Tuple[int, int]]],
    pieces: np.ndarray,
) -> Tuple[bool, Set[int]]:
    """Remove (pid) from all unplaced cells; tighten neighbor domains via
    edge-equality with the newly fixed cell.

    Returns (ok, touched_set) where touched_set is the set of cells whose
    domains changed (so their messages need re-init).
    """
    touched: Set[int] = set()
    # Remove the fixed piece-id from all unplaced cells
    for pos in range(N):
        if pos == fixed_pos or pos in placements:
            continue
        new_D = [(p, r) for p, r in domains[pos] if p != pid]
        if len(new_D) != len(domains[pos]):
            touched.add(pos)
            domains[pos] = new_D
            if not new_D:
                return False, touched
    # Edge-equality with neighbors
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


def main():
    puzzle = load()
    pieces = puzzle["pieces"]
    domains = build_domains(puzzle)
    edges_per_cell, pids_per_cell = precompute_state_info(puzzle, domains)
    pairs = adjacency_pairs()
    m_var2fac = fresh_messages_for_domains(domains, pairs)
    cell_to_pairs = build_cell_to_pairs(domains, pairs)

    placements: Dict[int, Tuple[int, int]] = {}
    for pos, pid, rot in puzzle["hints"]:
        placements[pos] = (pid, rot)

    avail = np.ones(256, dtype=np.float64)

    log = []
    t0 = time.time()
    batch_size = 8
    contradiction = False
    bp_iters_per_round = 30
    damping = 0.3

    print(f"Initial: placements={len(placements)} states={sum(len(d) for d in domains)}")
    print()

    round_idx = 0
    while len(placements) < N and not contradiction:
        round_idx += 1
        # Run BP for a fixed number of iters (warm-started)
        for it in range(bp_iters_per_round):
            change = bp_iteration_with_uniqueness(
                domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
                cell_to_pairs, avail, damping=damping,
            )
            if change < 1e-3:
                break
        # Update availability
        beliefs = compute_beliefs_with_uniqueness(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail,
        )
        avail = 0.5 * avail + 0.5 * piece_availability(beliefs, pids_per_cell)
        # One more BP pass with updated avail
        for it in range(10):
            change = bp_iteration_with_uniqueness(
                domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
                cell_to_pairs, avail, damping=damping,
            )
            if change < 1e-3:
                break
        beliefs = compute_beliefs_with_uniqueness(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail,
        )
        H = cell_entropies(beliefs)

        # Cascade-fix all D==1 cells first
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
                log.append({"event": "propagation_empty", "pos": pos,
                            "depth": len(placements)})
                break
            rebuild_cell_arrays_for(touched, domains, edges_per_cell, pids_per_cell, pieces)
        if contradiction:
            break

        # Pick top-K lowest-entropy non-placed cells. We pick cells whose
        # neighbors are *not all* getting fixed this batch — to avoid
        # adjacent-cell conflict where both are fixed greedily.
        if cascades:
            # Re-init messages for cells that may have been disrupted
            # by cascades (touched is union); we just re-init all messages
            # if many cascades for simplicity.
            m_var2fac = fresh_messages_for_domains(domains, pairs)
            cell_to_pairs = build_cell_to_pairs(domains, pairs)
            elapsed = time.time() - t0
            print(f"round {round_idx}: cascade-fixed {len(cascades)}, "
                  f"depth={len(placements)} t={elapsed:.1f}s")
            continue  # next round, re-run BP

        # Sort candidate cells by entropy
        candidates = sorted(
            ((H[p], p) for p in range(N)
             if p not in placements and len(domains[p]) >= 2),
            key=lambda x: x[0],
        )
        if not candidates:
            break

        # Fix top batch_size, but exclude conflicting adjacent picks
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
            # Check that pid is still available (not already picked this batch)
            already_picked_pids = {p for (_, p, _) in fixed_this_round}
            if pid in already_picked_pids:
                # Pick next best state for this cell
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
            # exclude neighbors
            for (nx, ny) in [(x, y-1), (x+1, y), (x, y+1), (x-1, y)]:
                if 0 <= nx < SIZE and 0 <= ny < SIZE:
                    excluded.add(ny * SIZE + nx)
            excluded.add(pos)
        # Apply fixes
        for pos, pid, rot in fixed_this_round:
            placements[pos] = (pid, rot)
            ok, touched = propagate_after_fix(pos, pid, rot, placements, domains, pieces)
            if not ok:
                contradiction = True
                log.append({"event": "propagation_empty_in_batch", "pos": pos,
                            "depth": len(placements)})
                break
            rebuild_cell_arrays_for(touched, domains, edges_per_cell, pids_per_cell, pieces)
            log.append({
                "event": "fix",
                "pos": pos, "pid": pid, "rot": rot,
                "H_before": float(H[pos]),
                "depth": len(placements),
                "t": time.time() - t0,
            })
        if contradiction:
            break

        # After a batch, re-init messages (cheap; ~25ms)
        m_var2fac = fresh_messages_for_domains(domains, pairs)
        cell_to_pairs = build_cell_to_pairs(domains, pairs)

        elapsed = time.time() - t0
        # Compute current edge-score
        score = compute_score(placements, pieces)
        print(f"round {round_idx}: batch_fixed={len(fixed_this_round)}, "
              f"depth={len(placements)}/256, score={score}/480, t={elapsed:.1f}s, "
              f"avg_H_remaining={H[~np.isin(np.arange(N), list(placements.keys()))].mean() if len(placements) < N else 0:.4f}")

    # Final report
    elapsed = time.time() - t0
    final_score = compute_score(placements, pieces)
    print()
    print(f"=== BP-decimation v2 finished ===")
    print(f"depth reached: {len(placements)}/256")
    print(f"final score: {final_score}/480")
    print(f"contradiction: {contradiction}")
    print(f"wall-clock: {elapsed:.1f}s")
    OUT = ROOT / "output" / "v11_sp" / "bp_decimation_v2_log.json"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "depth_reached": len(placements),
        "final_score": int(final_score),
        "contradiction": contradiction,
        "wall_clock_s": elapsed,
        "placements": [[int(pos), int(pid), int(rot)] for pos, (pid, rot) in placements.items()],
        "log": log,
    }
    with OUT.open("w") as f:
        json.dump(out, f, indent=2)
    print(f"saved {OUT.relative_to(ROOT)}")


def compute_score(placements, pieces) -> int:
    """Edge-match score over current placements."""
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


if __name__ == "__main__":
    main()
