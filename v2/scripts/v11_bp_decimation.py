#!/usr/bin/env python3
"""BP-decimation on E2: repeatedly fix the most-polarized cell.

Loop:
  while there are unfixed cells:
    run BP to convergence (with soft uniqueness)
    compute beliefs
    find non-hint, non-fixed cell with lowest entropy
    fix it to its argmax state
    propagate: remove now-incompatible states from neighbor domains,
               remove the chosen piece from all other cells' domains
    if any domain becomes empty → CONTRADICTION, log and stop
    if some cell's domain becomes size 1 → cascade-fix it for free
  end while

Score: count adjacent-cell edge-equality matches over the final assignment.
Stop on contradiction; report depth reached.
"""
from __future__ import annotations

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from v11_load_e2 import load
from v11_factor_graph import build_domains, adjacency_pairs, cell_class, SIZE, N
from v11_bp_uniq import (
    bp_iteration_with_uniqueness, compute_beliefs_with_uniqueness,
    piece_availability
)
from v11_bp import precompute_state_info, build_message_index, cell_entropies, EPS


def score_placements(placements: Dict[int, Tuple[int, int]],
                     edges_per_cell, domains) -> int:
    """Count edge matches across the placed cells.

    Two adjacent placed cells contribute 1 to score iff the touching edges
    match (color equality, both non-BORDER). Edges between a placed and
    unplaced cell don't count.
    """
    matched = 0
    # We need rotated edges per placement. State idx within domain.
    placement_edges: Dict[int, np.ndarray] = {}
    for pos, (pid, rot) in placements.items():
        D = domains[pos]
        # Find state idx
        for s, st in enumerate(D):
            if st == (pid, rot):
                placement_edges[pos] = edges_per_cell[pos][s]
                break
    for pos in placements:
        x, y = pos % SIZE, pos // SIZE
        if x + 1 < SIZE and (pos + 1) in placement_edges:
            if placement_edges[pos][1] == placement_edges[pos + 1][3] and placement_edges[pos][1] != 0:
                matched += 1
        if y + 1 < SIZE and (pos + SIZE) in placement_edges:
            if placement_edges[pos][2] == placement_edges[pos + SIZE][0] and placement_edges[pos][2] != 0:
                matched += 1
    return matched


def propagate_constraints(
    placements: Dict[int, Tuple[int, int]],
    fixed_pid: int,
    fixed_pos: int,
    domains: List[List[Tuple[int, int]]],
    edges_per_cell: List[np.ndarray],
    pids_per_cell: List[np.ndarray],
) -> bool:
    """After fixing `fixed_pos` to its (pid, rot) state, prune all other
    cells' domains:
      - remove all states containing `fixed_pid` from cells other than fixed_pos
      - for each neighbor of fixed_pos, remove states whose touching edge
        color disagrees with the fixed cell's touching edge color (BORDER vs
        non-BORDER is already enforced at domain-build time).

    Returns False if any domain becomes empty.
    """
    fixed_pid_, fixed_rot = placements[fixed_pos]
    assert fixed_pid_ == fixed_pid
    # Get rotated edges of the fixed cell
    D = domains[fixed_pos]
    s_idx = D.index((fixed_pid, fixed_rot))
    fixed_edges = edges_per_cell[fixed_pos][s_idx]

    # Remove piece from other cells
    for pos in range(N):
        if pos == fixed_pos or pos in placements:
            continue
        new_D = [(p, r) for p, r in domains[pos] if p != fixed_pid]
        if len(new_D) != len(domains[pos]):
            domains[pos] = new_D

    # Neighbor edge consistency
    x, y = fixed_pos % SIZE, fixed_pos // SIZE
    nbrs = [
        ((x, y - 1), 0, 2),  # neighbor up: my top must equal nbr's bottom
        ((x + 1, y), 1, 3),
        ((x, y + 1), 2, 0),
        ((x - 1, y), 3, 1),
    ]
    for (nx, ny), my_side, nb_side in nbrs:
        if not (0 <= nx < SIZE and 0 <= ny < SIZE):
            continue
        npos = ny * SIZE + nx
        if npos in placements:
            # Already fixed, edge consistency was checked at fix time.
            continue
        required_color = int(fixed_edges[my_side])
        # Filter neighbor domain
        new_D = []
        for (p, r) in domains[npos]:
            # Find state index in npos's domain
            # We need the edges to compute touching side color.
            # Lookup via brute search (slow but correct for a PoC).
            from v11_load_e2 import rotate_edges
            pe = rotate_edges(np.array([0, 0, 0, 0]), 0)  # placeholder
            # Just compute edge directly from piece-id and rotation
            edges = rotate_edges(np.copy(load_pieces_cache(p)), r)
            if edges[nb_side] == required_color:
                new_D.append((p, r))
        if not new_D:
            return False
        domains[npos] = new_D
        if len(new_D) == 0:
            return False
    # Rebuild edges_per_cell and pids_per_cell for affected cells
    return True


# Cache for piece edges
_PIECE_EDGES = None

def load_pieces_cache(pid: int = None):
    global _PIECE_EDGES
    if _PIECE_EDGES is None:
        p = load()
        _PIECE_EDGES = p["pieces"]
    if pid is None:
        return _PIECE_EDGES
    return _PIECE_EDGES[pid]


def rebuild_cell_arrays(domains, edges_per_cell, pids_per_cell):
    """Rebuild edges_per_cell and pids_per_cell after domain changes."""
    from v11_load_e2 import rotate_edges
    pieces = load_pieces_cache()
    for pos in range(N):
        D = domains[pos]
        n = len(D)
        E = np.zeros((n, 4), dtype=np.int8)
        P = np.zeros(n, dtype=np.int16)
        for i, (pid, rot) in enumerate(D):
            E[i, :] = rotate_edges(pieces[pid], rot)
            P[i] = pid
        edges_per_cell[pos] = E
        pids_per_cell[pos] = P


def run_bp_to_convergence(domains, edges_per_cell, pids_per_cell,
                          pairs, m_var2fac, cell_to_pairs, avail,
                          max_iter=80, tol=2e-3, damping=0.4):
    for it in range(1, max_iter + 1):
        change = bp_iteration_with_uniqueness(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail, damping=damping,
        )
        if change < tol:
            return it
    return max_iter


def main():
    puzzle = load()
    domains = build_domains(puzzle)
    edges_per_cell, pids_per_cell = precompute_state_info(puzzle, domains)
    pairs, m_var2fac, cell_to_pairs = build_message_index(domains)

    placements: Dict[int, Tuple[int, int]] = {}
    for pos, pid, rot in puzzle["hints"]:
        placements[pos] = (pid, rot)

    log = []
    contradiction = False
    avail = np.ones(256, dtype=np.float64)

    t0 = time.time()
    target_placements = N  # try to fix everything
    n_rebuild = 0
    while len(placements) < target_placements:
        # Run BP a couple of outer rounds with uniqueness to settle
        run_bp_to_convergence(domains, edges_per_cell, pids_per_cell,
                              pairs, m_var2fac, cell_to_pairs, avail)
        beliefs = compute_beliefs_with_uniqueness(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail
        )
        avail = 0.5 * avail + 0.5 * piece_availability(beliefs, pids_per_cell)
        run_bp_to_convergence(domains, edges_per_cell, pids_per_cell,
                              pairs, m_var2fac, cell_to_pairs, avail)
        beliefs = compute_beliefs_with_uniqueness(
            domains, edges_per_cell, pids_per_cell, pairs, m_var2fac,
            cell_to_pairs, avail
        )

        # Find lowest-entropy non-hint, non-placed cell
        H = cell_entropies(beliefs)
        # Skip placed and degenerate (D==1) cells; we'll cascade-fix D==1 separately
        best_pos = -1
        best_H = float("inf")
        for pos in range(N):
            if pos in placements:
                continue
            D = len(domains[pos])
            if D == 0:
                contradiction = True
                log.append({"event": "empty_domain", "pos": pos, "depth": len(placements)})
                break
            if D == 1:
                # Cascade-fix
                pid, rot = domains[pos][0]
                placements[pos] = (pid, rot)
                log.append({"event": "cascade_fix", "pos": pos, "pid": pid, "rot": rot,
                            "depth": len(placements)})
                # Need to break and rebuild
                best_pos = -2
                break
            if H[pos] < best_H:
                best_H = H[pos]
                best_pos = pos
        if contradiction:
            break
        if best_pos == -2:
            # Cascade fix happened; rebuild and continue
            # We also need to propagate the cascade-fix piece-removal
            # First do propagation
            for pos in list(placements.keys()):
                if pos not in placements:
                    continue
                pid, rot = placements[pos]
            # Re-propagate by rebuilding domains:
            # Remove all placed pieces from non-placed cells
            placed_pids = {pid for pid, _ in placements.values()}
            for pos in range(N):
                if pos in placements:
                    continue
                domains[pos] = [(p, r) for p, r in domains[pos] if p not in placed_pids]
                if not domains[pos]:
                    contradiction = True
                    log.append({"event": "empty_after_cascade", "pos": pos,
                                "depth": len(placements)})
                    break
            if contradiction:
                break
            # Also propagate edge constraints from all placed cells
            for ppos in placements:
                # Already done at fix-time; redo for cascade-fixed cells
                pass
            rebuild_cell_arrays(domains, edges_per_cell, pids_per_cell)
            pairs, m_var2fac, cell_to_pairs = build_message_index(domains)
            avail = np.ones(256, dtype=np.float64)
            n_rebuild += 1
            continue
        if best_pos < 0:
            break

        # Fix best_pos to its argmax state
        b = beliefs[best_pos]
        s_idx = int(np.argmax(b))
        pid, rot = domains[best_pos][s_idx]
        placements[best_pos] = (pid, rot)

        elapsed = time.time() - t0
        log.append({"event": "fix", "pos": best_pos, "pid": pid, "rot": rot,
                    "H": float(best_H), "depth": len(placements),
                    "t": elapsed})
        if len(placements) % 10 == 0 or len(placements) <= 20:
            score = score_placements(placements, edges_per_cell, domains)
            print(f"depth={len(placements)} pos=({best_pos%SIZE},{best_pos//SIZE}) "
                  f"pid={pid} rot={rot} H={best_H:.4f} score≈{score} t={elapsed:.1f}s")

        # Propagate: remove this piece from other cells, edge constraints to neighbors
        # Remove piece from all unplaced cells
        for pos in range(N):
            if pos == best_pos or pos in placements:
                continue
            new_D = [(p, r) for p, r in domains[pos] if p != pid]
            domains[pos] = new_D
        # Edge constraints
        from v11_load_e2 import rotate_edges
        pieces = puzzle["pieces"]
        fixed_edges = rotate_edges(pieces[pid], rot)
        x, y = best_pos % SIZE, best_pos // SIZE
        nbrs = [
            ((x, y - 1), 0, 2),
            ((x + 1, y), 1, 3),
            ((x, y + 1), 2, 0),
            ((x - 1, y), 3, 1),
        ]
        for (nx, ny), my_side, nb_side in nbrs:
            if not (0 <= nx < SIZE and 0 <= ny < SIZE):
                continue
            npos = ny * SIZE + nx
            if npos in placements:
                continue
            req = int(fixed_edges[my_side])
            new_D = []
            for (p, r) in domains[npos]:
                # Compute edge of piece p rotated r at side nb_side
                e = rotate_edges(pieces[p], r)
                if e[nb_side] == req:
                    new_D.append((p, r))
            domains[npos] = new_D
            if not new_D:
                contradiction = True
                log.append({"event": "empty_neighbor", "pos": npos,
                            "depth": len(placements)})
                break
        if contradiction:
            break

        rebuild_cell_arrays(domains, edges_per_cell, pids_per_cell)
        pairs, m_var2fac, cell_to_pairs = build_message_index(domains)
        # Reset availability since piece set changed
        avail = np.ones(256, dtype=np.float64)

    final_score = score_placements(placements, edges_per_cell, domains)
    print()
    print(f"=== BP-decimation finished ===")
    print(f"depth reached: {len(placements)}")
    print(f"final score (edge-matches): {final_score}")
    print(f"contradiction: {contradiction}")
    print(f"rebuild events: {n_rebuild}")
    print(f"wall-clock: {time.time()-t0:.1f}s")

    OUT = ROOT / "output" / "v11_sp" / "bp_decimation_log.json"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "depth_reached": len(placements),
        "final_score": int(final_score),
        "contradiction": contradiction,
        "rebuilds": n_rebuild,
        "wall_clock_s": time.time() - t0,
        "log": log,
        "placements": [(pos, pid, rot) for pos, (pid, rot) in placements.items()],
    }
    with OUT.open("w") as f:
        json.dump(out, f, indent=2)
    print(f"Saved log to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
