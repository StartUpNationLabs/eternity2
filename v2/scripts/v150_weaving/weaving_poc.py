#!/usr/bin/env python3
"""V150 — WEAVING PoC.

Two-axis consensus construction. See vault/concepts/weaving-consensus.md
for the math.

Algorithm:
  1. build_row_greedy(seed) → board B_R
  2. build_col_greedy(seed) → board B_C
  3. tension(B_R, B_C) → int (number of disagreeing cells)
  4. consensus_iterate(B_R, B_C) → reduce tension while preserving score

We measure:
  - score(B_R), score(B_C) initially.
  - initial tension.
  - final score after consensus.
  - final tension.
"""

from __future__ import annotations
import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_csv(p):
    BORDER_RAW = 65535
    pieces = []
    with open(p) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            sides = [int(s.strip(), 2) for s in parts[:4]]
            sides = [0 if v == BORDER_RAW else v for v in sides]
            pieces.append(tuple(sides))
    return size, pieces


def rotate(p, r):
    n, e, s, w = p
    return [(n, e, s, w), (e, s, w, n), (s, w, n, e), (w, n, e, s)][r]


def needed_zero_sides(pos, size):
    r, c = pos // size, pos % size
    sides = set()
    if r == 0: sides.add(0)
    if c == size - 1: sides.add(1)
    if r == size - 1: sides.add(2)
    if c == 0: sides.add(3)
    return sides


def piece_class(p):
    n_border = sum(1 for s in p if s == 0)
    if n_border == 2: return "corner"
    if n_border == 1: return "edge"
    return "interior"


def cell_class(pos, size):
    r, c = pos // size, pos % size
    is_corner = (r == 0 or r == size - 1) and (c == 0 or c == size - 1)
    is_border = r == 0 or r == size - 1 or c == 0 or c == size - 1
    if is_corner: return "corner"
    if is_border: return "edge"
    return "interior"


def valid_rotations(piece, pos, size):
    """All rotations of piece that satisfy border constraints at pos.
    Returns list of (rotation_index, rotated_tuple)."""
    needed = needed_zero_sides(pos, size)
    out = []
    for r in range(4):
        rot = rotate(piece, r)
        if not all(rot[s] == 0 for s in needed):
            continue
        if not all(rot[s] != 0 for s in range(4) if s not in needed):
            continue
        out.append((r, rot))
    return out


def edge_match_at(pos, rot_tuple, board, size):
    """Count matched edges between (pos, rot_tuple) and placed neighbours."""
    r, c = pos // size, pos % size
    m = 0
    # N
    if r > 0:
        n_cell = board[pos - size]
        if n_cell is not None:
            n_rot = n_cell[1]
            if n_rot[2] == rot_tuple[0] and rot_tuple[0] != 0:
                m += 1
    # E
    if c < size - 1:
        e_cell = board[pos + 1]
        if e_cell is not None:
            e_rot = e_cell[1]
            if e_rot[3] == rot_tuple[1] and rot_tuple[1] != 0:
                m += 1
    # S
    if r < size - 1:
        s_cell = board[pos + size]
        if s_cell is not None:
            s_rot = s_cell[1]
            if s_rot[0] == rot_tuple[2] and rot_tuple[2] != 0:
                m += 1
    # W
    if c > 0:
        w_cell = board[pos - 1]
        if w_cell is not None:
            w_rot = w_cell[1]
            if w_rot[1] == rot_tuple[3] and rot_tuple[3] != 0:
                m += 1
    return m


def edge_constraint_at(pos, board, size):
    """Returns (n_color, e_color, s_color, w_color) where each is the
    required color from already-placed neighbours, or None if free.
    Also (-1) when the side faces OOB (must be border)."""
    r, c = pos // size, pos % size
    n_col = -1 if r == 0 else (board[pos - size][1][2] if board[pos - size] else None)
    e_col = -1 if c == size - 1 else (board[pos + 1][1][3] if board[pos + 1] else None)
    s_col = -1 if r == size - 1 else (board[pos + size][1][0] if board[pos + size] else None)
    w_col = -1 if c == 0 else (board[pos - 1][1][1] if board[pos - 1] else None)
    return n_col, e_col, s_col, w_col


def best_rotation_for_cell(piece, pos, board, size, prefer_axis="horizontal"):
    """Among valid rotations of piece at pos, pick the one maximizing
    edge match with placed neighbours. prefer_axis breaks ties (gives
    +0.01 weight to horizontal vs vertical edges for row-greedy)."""
    candidates = valid_rotations(piece, pos, size)
    if not candidates:
        return None
    best = None
    best_score = -1.0
    for rot_idx, rot in candidates:
        # Hard constraint check against placed neighbours.
        n_c, e_c, s_c, w_c = edge_constraint_at(pos, board, size)
        if n_c is not None and n_c >= 0 and rot[0] != n_c: continue
        if n_c == -1 and rot[0] != 0: continue
        if e_c is not None and e_c >= 0 and rot[1] != e_c: continue
        if e_c == -1 and rot[1] != 0: continue
        if s_c is not None and s_c >= 0 and rot[2] != s_c: continue
        if s_c == -1 and rot[2] != 0: continue
        if w_c is not None and w_c >= 0 and rot[3] != w_c: continue
        if w_c == -1 and rot[3] != 0: continue
        m = edge_match_at(pos, rot, board, size)
        score = float(m)
        if prefer_axis == "horizontal":
            # Slight bonus if the E or W side matches.
            # (For row-greedy, in-row matches are W neighbour matches.)
            pass  # m already captures all 4 sides; axis preference is in scan order not value-order.
        if score > best_score:
            best_score = score
            best = (rot_idx, rot, m)
    return best


def build_greedy(pieces, size, seed, scan_order, allow_mismatch=True):
    """Generic greedy builder. scan_order: list of N*N positions to visit in order.

    If allow_mismatch=True (default), uses a SOFT constraint: pieces must
    satisfy border constraints (zero sides at perimeter), but otherwise
    we maximize matched-edges and place SOMETHING at every cell, even
    if it means a mismatch. This avoids early dead-ends.
    """
    rng = random.Random(seed)
    n = size * size
    board = [None] * n
    inventory = set(range(len(pieces)))
    placement_log = []
    for pos in scan_order:
        rc = cell_class(pos, size)
        best_choice = None
        best_match = -1
        pids = list(inventory)
        rng.shuffle(pids)
        for pid in pids:
            piece = pieces[pid]
            if piece_class(piece) != rc:
                continue
            # Iterate valid rotations (border constraints).
            cands = valid_rotations(piece, pos, size)
            for rot_idx, rot in cands:
                if not allow_mismatch:
                    # Hard constraint against placed neighbours.
                    n_c, e_c, s_c, w_c = edge_constraint_at(pos, board, size)
                    if n_c is not None and n_c >= 0 and rot[0] != n_c: continue
                    if e_c is not None and e_c >= 0 and rot[1] != e_c: continue
                    if s_c is not None and s_c >= 0 and rot[2] != s_c: continue
                    if w_c is not None and w_c >= 0 and rot[3] != w_c: continue
                m = edge_match_at(pos, rot, board, size)
                if m > best_match:
                    best_match = m
                    best_choice = (pos, pid, rot_idx, rot)
        if best_choice is None:
            placement_log.append((pos, None))
            break
        ppos, pid, rot_idx, rot = best_choice
        board[ppos] = (pid, rot, rot_idx)
        inventory.discard(pid)
        placement_log.append((ppos, pid))
    return board, placement_log


def row_major_scan(size):
    return list(range(size * size))


def col_major_scan(size):
    """Visit (0,0), (1,0), (2,0), ..., (size-1, 0), (0, 1), ..."""
    out = []
    for c in range(size):
        for r in range(size):
            out.append(r * size + c)
    return out


def score(board, size):
    """Matched-edges score of a (possibly incomplete) board."""
    matched = 0
    for r in range(size):
        for c in range(size):
            pos = r * size + c
            if board[pos] is None:
                continue
            rot = board[pos][1]
            if c < size - 1:
                rp = board[pos + 1]
                if rp is not None and rp[1][3] == rot[1] and rot[1] != 0:
                    matched += 1
            if r < size - 1:
                sp = board[pos + size]
                if sp is not None and sp[1][0] == rot[2] and rot[2] != 0:
                    matched += 1
    return matched


def tension(B_R, B_C):
    """Number of cells where the two boards disagree on piece_id."""
    t = 0
    for cR, cC in zip(B_R, B_C):
        if cR is None or cC is None:
            t += 1
            continue
        if cR[0] != cC[0]:
            t += 1
    return t


def find_piece_pos(board, target_pid):
    """Return pos in board where piece target_pid is placed, or None."""
    for pos, cell in enumerate(board):
        if cell is not None and cell[0] == target_pid:
            return pos
    return None


def best_rotation_unconstrained(piece, pos, board, size):
    """Best rotation of piece at pos respecting border constraints and
    maximizing edge match to placed neighbours. Returns (rot_idx, rot_tuple, m_matches)."""
    cands = valid_rotations(piece, pos, size)
    best = None
    best_m = -1
    for rot_idx, rot in cands:
        m = edge_match_at(pos, rot, board, size)
        if m > best_m:
            best_m = m
            best = (rot_idx, rot, m)
    return best


def try_tension_swap(board_target, source_pid_to_inject, pos_to_inject, size, pieces):
    """In board_target, swap the piece currently at pos_to_inject with
    the source_pid_to_inject (which already lives elsewhere in
    board_target). After swap:
      - source_pid_to_inject lives at pos_to_inject.
      - original piece at pos_to_inject lives at the OLD location of
        source_pid_to_inject.
    Rotations re-optimised at both affected positions.
    Returns (delta_score, new_board) — or (None, None) if no valid swap.
    """
    old_at_target = board_target[pos_to_inject]
    if old_at_target is None or old_at_target[0] == source_pid_to_inject:
        return None, None
    other_pos = find_piece_pos(board_target, source_pid_to_inject)
    if other_pos is None:
        return None, None
    # Cell class compatibility.
    if cell_class(pos_to_inject, size) != piece_class(pieces[source_pid_to_inject]):
        return None, None
    if cell_class(other_pos, size) != piece_class(pieces[old_at_target[0]]):
        return None, None
    # Build trial board.
    trial = list(board_target)
    # Temporarily clear both cells.
    trial[pos_to_inject] = None
    trial[other_pos] = None
    # Place source_pid at pos_to_inject (best rotation).
    r1 = best_rotation_unconstrained(pieces[source_pid_to_inject], pos_to_inject, trial, size)
    if r1 is None: return None, None
    trial[pos_to_inject] = (source_pid_to_inject, r1[1], r1[0])
    # Place old_at_target piece at other_pos (best rotation).
    r2 = best_rotation_unconstrained(pieces[old_at_target[0]], other_pos, trial, size)
    if r2 is None:
        return None, None
    trial[other_pos] = (old_at_target[0], r2[1], r2[0])
    # Score delta = score(trial) - score(board_target). But computing
    # full score is N². Compute local delta around both swapped cells.
    # Simpler/correct: full rescore.
    old_score = score(board_target, size)
    new_score = score(trial, size)
    delta = new_score - old_score
    return delta, trial


def consensus_iterate(B_R, B_C, size, pieces, max_iters=200, eps_R=0, eps_C=0, verbose=False):
    """Iteratively reduce tension between B_R and B_C while preserving
    or improving each board's score by at least -eps."""
    B_R = list(B_R)
    B_C = list(B_C)
    n_accepted_R = 0
    n_accepted_C = 0

    for it in range(max_iters):
        tension_cells = [pos for pos in range(size * size)
                         if B_R[pos] is not None and B_C[pos] is not None
                         and B_R[pos][0] != B_C[pos][0]]
        if not tension_cells:
            if verbose: print(f"  consensus reached at iter {it}", flush=True)
            break
        # Pick a random tension cell.
        random.shuffle(tension_cells)
        progress = False
        for pos in tension_cells:
            # Try injecting B_C's piece into B_R at pos.
            target_pid_for_R = B_C[pos][0]
            d_R, trial_R = try_tension_swap(B_R, target_pid_for_R, pos, size, pieces)
            if d_R is not None and d_R >= -eps_R:
                # Try injecting B_R's piece into B_C at pos (symmetric).
                # Note: by symmetry the swap goes the other way.
                target_pid_for_C = trial_R[pos][0]  # ← what B_R now has at pos = the injected pid
                # actually we want B_C to ADOPT the piece B_R now has, but that's what we just put in B_R.
                # Simpler: just commit the R-side swap and let next iter handle C.
                B_R = trial_R
                n_accepted_R += 1
                progress = True
                break
            # Try the symmetric direction (inject B_R into B_C).
            target_pid_for_C = B_R[pos][0]
            d_C, trial_C = try_tension_swap(B_C, target_pid_for_C, pos, size, pieces)
            if d_C is not None and d_C >= -eps_C:
                B_C = trial_C
                n_accepted_C += 1
                progress = True
                break
        if not progress:
            if verbose: print(f"  no progress at iter {it}, tension={len(tension_cells)}", flush=True)
            break
        if verbose and (it + 1) % 20 == 0:
            print(f"  iter {it+1}: tension={len(tension_cells)}, "
                  f"score_R={score(B_R, size)}, score_C={score(B_C, size)}", flush=True)

    return B_R, B_C, n_accepted_R, n_accepted_C


def total_interior_edges(size):
    return (size - 1) * size + size * (size - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--seeds", type=str, default="42,1,7,13,99")
    args = ap.parse_args()

    size, pieces = load_csv(args.puzzle)
    target = total_interior_edges(size)
    print(f"[v150] puzzle: {size}×{size}, pieces={len(pieces)}, target={target}", flush=True)
    print()

    row_scan = row_major_scan(size)
    col_scan = col_major_scan(size)

    seeds = [int(s) for s in args.seeds.split(",")]
    rows_results = []
    cols_results = []
    tensions = []

    final_R_scores = []
    final_C_scores = []
    final_best_scores = []
    final_tensions = []

    print(f"[v150] running {len(seeds)} seeds × (row-greedy + col-greedy + consensus)", flush=True)
    print(f"  seed  R0  C0  T0    iter   R1   C1   T1   best")
    for seed in seeds:
        random.seed(seed)
        t0 = time.time()
        B_R, log_R = build_greedy(pieces, size, seed, row_scan)
        B_C, log_C = build_greedy(pieces, size, seed, col_scan)
        s_R0 = score(B_R, size)
        s_C0 = score(B_C, size)
        T0 = tension(B_R, B_C)
        rows_results.append((s_R0, sum(1 for b in B_R if b is not None), 0))
        cols_results.append((s_C0, sum(1 for b in B_C if b is not None), 0))
        tensions.append(T0)
        # Consensus iteration. Allow up to 5-point degradation per swap
        # to escape local minima (simulated-annealing-lite).
        B_R2, B_C2, n_R, n_C = consensus_iterate(B_R, B_C, size, pieces, max_iters=2000, eps_R=5, eps_C=5)
        s_R1 = score(B_R2, size)
        s_C1 = score(B_C2, size)
        T1 = tension(B_R2, B_C2)
        best = max(s_R1, s_C1)
        t_total = time.time() - t0
        final_R_scores.append(s_R1)
        final_C_scores.append(s_C1)
        final_best_scores.append(best)
        final_tensions.append(T1)
        print(f"  {seed:5d}  {s_R0:3d} {s_C0:3d}  {T0:3d}   {n_R+n_C:5d}  {s_R1:3d}  {s_C1:3d}  {T1:3d}  {best:3d}  ({t_total:.1f}s)", flush=True)

    print()
    print(f"[v150] aggregates:")
    s_Rs = [r[0] for r in rows_results]
    s_Cs = [r[0] for r in cols_results]
    print(f"  row-greedy (initial):  min={min(s_Rs)} med={sorted(s_Rs)[len(s_Rs)//2]} max={max(s_Rs)}")
    print(f"  col-greedy (initial):  min={min(s_Cs)} med={sorted(s_Cs)[len(s_Cs)//2]} max={max(s_Cs)}")
    print(f"  initial tension:       min={min(tensions)} med={sorted(tensions)[len(tensions)//2]} max={max(tensions)}")
    print(f"  WEAVING best after consensus:")
    print(f"      min={min(final_best_scores)} med={sorted(final_best_scores)[len(final_best_scores)//2]} max={max(final_best_scores)}")
    print(f"  final tension:         min={min(final_tensions)} med={sorted(final_tensions)[len(final_tensions)//2]} max={max(final_tensions)}")
    print()
    # Comparison.
    baseline = sorted(s_Rs + s_Cs)[len(s_Rs+s_Cs)//2]
    after = sorted(final_best_scores)[len(final_best_scores)//2]
    print(f"[v150] median Δ (consensus vs initial best-axis): {after - max(sorted(s_Rs+s_Cs)[-len(seeds):][len(seeds)//2:][0], baseline):+d}")
    print(f"[v150] best WEAVING: {max(final_best_scores)}/480 ({max(final_best_scores)/target*100:.1f}%) vs GRAIN PoC ceiling 373")


if __name__ == "__main__":
    main()
