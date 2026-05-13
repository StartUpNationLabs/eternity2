#!/usr/bin/env python3
"""
N5 step 1: analyse the mismatch patch of a 457 board.

For the given 457 board:
- compute placed pieces and rotations
- identify cells with >=1 unmatched edge (mismatch cells)
- compute the 4-adjacency component structure of the mismatch graph
- for each mismatch cell, count how many pieces in the BAG could replace it
  given fixed neighbors (= local candidate set size)
- estimate whether exact patch enumeration is feasible

Output: structural map of the 457-locked region.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")

BOARD_JSON = ROOT / "output/v17_alns_pt/pt_winning5_n4_t1_30_s1_1778661199.json"
PUZZLE_CSV = ROOT.parent / "data/puzzles/size_16_official_eternity.csv"
SIZE = 16
N_CELLS = SIZE * SIZE


BORDER_RAW = 65535  # CSV-encoded BORDER value (= 0 internally in the engine)


def parse_color(s):
    """65535 -> 0 (BORDER); else the 16-bit value as a small int."""
    v = int(s, 2)
    if v == BORDER_RAW:
        return 0
    return v


def load_pieces():
    """Load piece edges from CSV. Returns list of (north, east, south, west) tuples (engine-encoding)."""
    pieces = []
    with open(PUZZLE_CSV) as f:
        reader = csv.reader(f)
        size_row = next(reader)
        assert int(size_row[0]) == SIZE
        for row in reader:
            if not row or len(row) < 4:
                continue
            edges = tuple(parse_color(s) for s in row[:4])
            pieces.append(edges)
    return pieces


BORDER = 0


def rotate_edges(edges, rot):
    """Rotate edges (N, E, S, W) clockwise by rot * 90 degrees."""
    n, e, s, w = edges
    if rot == 0:
        return (n, e, s, w)
    elif rot == 1:
        return (w, n, e, s)
    elif rot == 2:
        return (s, w, n, e)
    elif rot == 3:
        return (e, s, w, n)
    else:
        raise ValueError(rot)


def load_board():
    d = json.load(open(BOARD_JSON))
    placement = d["placement"]
    board = [None] * N_CELLS
    for c in placement:
        pos = c["pos"]
        pid = c["piece_id"]
        rot = c["rotation"]
        board[pos] = (pid, rot)
    return board, d.get("matched_best")


def count_mismatches(board, pieces):
    """Return list of (pos, n_unmatched_edges) and total edge mismatches."""
    mismatches = []
    edge_mismatches = 0
    for pos in range(N_CELLS):
        cell = board[pos]
        if cell is None:
            continue
        pid, rot = cell
        N, E, S, W = rotate_edges(pieces[pid], rot)
        row = pos // SIZE
        col = pos % SIZE
        unmatched_here = 0

        # North neighbor (above)
        if row > 0:
            np = board[pos - SIZE]
            if np:
                npid, nrot = np
                _, _, ns, _ = rotate_edges(pieces[npid], nrot)
                # our N must match neighbor's S
                if N != BORDER and ns != BORDER and N != ns:
                    unmatched_here += 1

        # East neighbor (right)
        if col < SIZE - 1:
            np = board[pos + 1]
            if np:
                npid, nrot = np
                _, _, _, nw = rotate_edges(pieces[npid], nrot)
                if E != BORDER and nw != BORDER and E != nw:
                    unmatched_here += 1

        # South neighbor (below)
        if row < SIZE - 1:
            np = board[pos + SIZE]
            if np:
                npid, nrot = np
                nn, _, _, _ = rotate_edges(pieces[npid], nrot)
                if S != BORDER and nn != BORDER and S != nn:
                    unmatched_here += 1

        # West neighbor (left)
        if col > 0:
            np = board[pos - 1]
            if np:
                npid, nrot = np
                _, ne, _, _ = rotate_edges(pieces[npid], nrot)
                if W != BORDER and ne != BORDER and W != ne:
                    unmatched_here += 1

        if unmatched_here > 0:
            mismatches.append((pos, unmatched_here))
            edge_mismatches += unmatched_here

    # Each edge counted twice (once from each side); divide by 2.
    return mismatches, edge_mismatches // 2


def find_components(mismatch_cells):
    """4-adjacency components of mismatch cells."""
    cells = set(mismatch_cells)
    visited = set()
    components = []
    for c in sorted(cells):
        if c in visited:
            continue
        comp = []
        stack = [c]
        while stack:
            cur = stack.pop()
            if cur in visited or cur not in cells:
                continue
            visited.add(cur)
            comp.append(cur)
            row, col = cur // SIZE, cur % SIZE
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = row + dr, col + dc
                if 0 <= nr < SIZE and 0 <= nc < SIZE:
                    npos = nr * SIZE + nc
                    if npos in cells and npos not in visited:
                        stack.append(npos)
        components.append(comp)
    components.sort(key=lambda c: -len(c))
    return components


def candidate_set(pos, board, pieces, bag):
    """For position pos: enumerate (pid in bag, rot) such that all 4 edges
    are compatible with currently-placed neighbors (or are border-consistent)."""
    row, col = pos // SIZE, pos % SIZE
    candidates = []

    # Determine required edges:
    # - If at edge of board, that side must be BORDER.
    # - If neighbor placed, that side must match neighbor's facing edge.
    # - Else: any value.
    constraints = [None, None, None, None]  # N, E, S, W
    if row == 0:
        constraints[0] = BORDER
    else:
        np = board[pos - SIZE]
        if np:
            npid, nrot = np
            _, _, ns, _ = rotate_edges(pieces[npid], nrot)
            constraints[0] = ns
    if col == SIZE - 1:
        constraints[1] = BORDER
    else:
        np = board[pos + 1]
        if np:
            npid, nrot = np
            _, _, _, nw = rotate_edges(pieces[npid], nrot)
            constraints[1] = nw
    if row == SIZE - 1:
        constraints[2] = BORDER
    else:
        np = board[pos + SIZE]
        if np:
            npid, nrot = np
            nn, _, _, _ = rotate_edges(pieces[npid], nrot)
            constraints[2] = nn
    if col == 0:
        constraints[3] = BORDER
    else:
        np = board[pos - 1]
        if np:
            npid, nrot = np
            _, ne, _, _ = rotate_edges(pieces[npid], nrot)
            constraints[3] = ne

    for pid in bag:
        for rot in range(4):
            edges = rotate_edges(pieces[pid], rot)
            ok = True
            for i in range(4):
                if constraints[i] is not None and edges[i] != constraints[i]:
                    ok = False
                    break
            if ok:
                candidates.append((pid, rot))
    return candidates, constraints


def main():
    print(f"Loading puzzle pieces from {PUZZLE_CSV}")
    pieces = load_pieces()
    print(f"  {len(pieces)} pieces loaded")

    print(f"Loading board from {BOARD_JSON.name}")
    board, score = load_board()
    placed = sum(1 for c in board if c is not None)
    print(f"  matched={score}, placed={placed}/{N_CELLS}")

    print(f"\nMismatch analysis:")
    mismatches, total_edge_mm = count_mismatches(board, pieces)
    print(f"  Cells with >=1 unmatched edge: {len(mismatches)}")
    print(f"  Total unmatched edges (pairs): {total_edge_mm}")
    print(f"  Score check: 480 (max) - {total_edge_mm} = {480 - total_edge_mm}")
    if score != 480 - total_edge_mm:
        print(f"  ⚠ MISMATCH with reported score {score}")

    # Mismatch cell distribution by row
    mismatch_positions = [m[0] for m in mismatches]
    row_dist = Counter(p // SIZE for p in mismatch_positions)
    print(f"\n  Mismatch cells by row:")
    for row in range(SIZE):
        n = row_dist.get(row, 0)
        bar = "#" * n
        print(f"    row {row:2d}: {n:2d}  {bar}")

    # Components
    components = find_components(mismatch_positions)
    print(f"\n  Connected components ({len(components)}):")
    for i, comp in enumerate(components):
        rows = sorted(set(p // SIZE for p in comp))
        cols = sorted(set(p % SIZE for p in comp))
        print(f"    Comp {i}: size {len(comp)}, rows {rows[0]}-{rows[-1]}, cols {cols[0]}-{cols[-1]}")

    # Candidate set per mismatch cell (assuming neighbors stay fixed,
    # which is the "single-cell swap" question)
    bag_used = set(c[0] for c in board if c is not None)
    bag_all = set(range(len(pieces)))
    bag_free_under_current_placement = []  # for each pos, we consider swapping it OUT, so bag = others
    # But for single-cell SWAP analysis: the bag of "alternative pieces" for pos p
    # is the set of pieces NOT at any other position.
    # For each pos that is itself in mismatch set, evaluate the SWAP options.

    print(f"\n  Per-cell candidate-set sizes (fixing neighbors, scanning bag = full piece set):")
    cand_sizes = []
    locked_cells = []
    one_choice_cells = []
    for pos, _ in mismatches:
        cell = board[pos]
        if cell is None:
            continue
        cur_pid = cell[0]
        # bag for THIS position = all pieces not used elsewhere, plus current piece.
        bag_for_pos = (bag_all - bag_used) | {cur_pid}
        cands, constraints = candidate_set(pos, board, pieces, bag_for_pos)
        cand_sizes.append((pos, len(cands), cands, constraints))
        if len(cands) == 1:
            locked_cells.append((pos, cands[0]))
        elif len(cands) == 0:
            one_choice_cells.append(pos)

    cand_sizes.sort(key=lambda x: -x[1])
    print(f"    Top 20 cells by candidate count:")
    for pos, k, cands, constraints in cand_sizes[:20]:
        row, col = pos // SIZE, pos % SIZE
        cur = board[pos]
        in_cands = (cur[0], cur[1]) in cands if cur else False
        print(f"      ({row:2d},{col:2d}) pos={pos:3d}  k={k:3d}  current={cur} in_cands={in_cands}  constraints={constraints}")
    print(f"\n    Cells with EXACTLY 1 candidate (uniquely determined): {len(locked_cells)}")
    print(f"    Cells with ZERO candidates (over-constrained): {len(one_choice_cells)}")
    print(f"    Median candidate count: {sorted([x[1] for x in cand_sizes])[len(cand_sizes)//2]}")
    print(f"    Distribution: min={min(x[1] for x in cand_sizes)}, max={max(x[1] for x in cand_sizes)}, sum={sum(x[1] for x in cand_sizes)}")

    # Redo: enumerate candidates that match as many edges as possible
    # (not requiring all 4). For each mismatch cell, find the best k = max
    # match-count achievable by swapping in any piece in bag.
    print(f"\n  REDONE candidate analysis — best-match per cell (mismatched edges relaxed):")
    print(f"  For each mismatch cell pos: find max-match-count piece (pid, rot) from bag.")

    def edge_count(edges, constraints):
        return sum(
            1
            for i in range(4)
            if constraints[i] is not None
            and edges[i] != BORDER
            and constraints[i] != BORDER
            and edges[i] == constraints[i]
        )

    # Compute constraints for each mismatch cell.
    cell_data = []
    for pos, _ in mismatches:
        cur = board[pos]
        if cur is None:
            continue
        cur_pid, cur_rot = cur
        row, col = pos // SIZE, pos % SIZE
        # Re-derive constraints (same as candidate_set).
        constraints = [None, None, None, None]
        if row == 0:
            constraints[0] = BORDER
        else:
            np = board[pos - SIZE]
            if np:
                _, _, ns, _ = rotate_edges(pieces[np[0]], np[1])
                constraints[0] = ns
        if col == SIZE - 1:
            constraints[1] = BORDER
        else:
            np = board[pos + 1]
            if np:
                _, _, _, nw = rotate_edges(pieces[np[0]], np[1])
                constraints[1] = nw
        if row == SIZE - 1:
            constraints[2] = BORDER
        else:
            np = board[pos + SIZE]
            if np:
                nn, _, _, _ = rotate_edges(pieces[np[0]], np[1])
                constraints[2] = nn
        if col == 0:
            constraints[3] = BORDER
        else:
            np = board[pos - 1]
            if np:
                _, ne, _, _ = rotate_edges(pieces[np[0]], np[1])
                constraints[3] = ne

        cur_edges = rotate_edges(pieces[cur_pid], cur_rot)
        cur_match = edge_count(cur_edges, constraints)
        # The maximum theoretical: count constraints that are non-border-non-None.
        max_possible = sum(1 for c in constraints if c is not None and c != BORDER)

        # Try all pieces in bag (= unused + current) for max match
        bag = (bag_all - bag_used) | {cur_pid}
        best_by_match = defaultdict(list)  # match_count -> list of (pid, rot)
        for pid in bag:
            for rot in range(4):
                e = rotate_edges(pieces[pid], rot)
                # Skip if border-incompatible.
                border_ok = True
                for i in range(4):
                    if constraints[i] == BORDER and e[i] != BORDER:
                        border_ok = False
                        break
                    if constraints[i] is not None and constraints[i] != BORDER and e[i] == BORDER:
                        border_ok = False
                        break
                if not border_ok:
                    continue
                m = edge_count(e, constraints)
                best_by_match[m].append((pid, rot))

        max_match = max(best_by_match.keys()) if best_by_match else 0
        best_options = best_by_match.get(max_match, [])
        cell_data.append({
            "pos": pos,
            "row": row,
            "col": col,
            "current": (cur_pid, cur_rot),
            "current_match": cur_match,
            "max_possible": max_possible,
            "max_match_achievable": max_match,
            "best_count": len(best_options),
            "best_options": best_options[:5],
            "current_is_optimal": cur_match == max_match,
            "improvement": max_match - cur_match,
            "constraints": constraints,
        })

    cell_data.sort(key=lambda x: -x["improvement"])
    print(f"\n  Sorted by potential improvement (single-cell swap):")
    print(f"  pos  (r,c)  current=(pid,rot) match  best  improv max_poss  alt_options")
    n_improvable = 0
    n_zero = 0
    for cd in cell_data:
        flag = ""
        if cd["improvement"] > 0:
            n_improvable += 1
            flag = " <-- IMPROVE"
        if cd["max_match_achievable"] == 0:
            n_zero += 1
        opts_str = f"{cd['best_count']} opts, e.g. {cd['best_options'][:2]}"
        print(f"  {cd['pos']:3d}  ({cd['row']:2d},{cd['col']:2d})  {str(cd['current']):10s}  {cd['current_match']}     {cd['max_match_achievable']}     {cd['improvement']:+d}      {cd['max_possible']}    {opts_str}{flag}")
    print(f"\n  Improvable single-cell-swap cells: {n_improvable}")
    print(f"  Cells where no piece in bag matches any edge: {n_zero}")

    # The KEY observation: even non-improving cells with multiple options at
    # same match level are "loose" — meaning swapping doesn't help LOCAL score
    # but might help via cascading downstream.
    print(f"\n  Cells with MULTIPLE pieces tied for max match (loose cells):")
    loose = [cd for cd in cell_data if cd["best_count"] > 1]
    print(f"  Found {len(loose)} loose cells (>=2 ties at best match level).")
    for cd in loose[:10]:
        print(f"    pos={cd['pos']} ({cd['row']},{cd['col']}) match={cd['max_match_achievable']} options={cd['best_count']}")

    # Also count: how many DIFFERENT pieces in the bag could fill ANY mismatch
    # cell at max-match? This is the "flexibility headcount".
    pieces_with_a_home = set()
    for cd in cell_data:
        for pid, _ in cd["best_options"]:
            pieces_with_a_home.add(pid)
    print(f"\n  Distinct pieces that appear as a best-match option in any mismatch cell: {len(pieces_with_a_home)}")
    print(f"  Bag size (unused + current placed at mismatch cells): {len(bag_all - bag_used) + len(mismatches)}")

    # Save full structural data.
    out_path = ROOT / "output/n5_patch/patch_data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "board_file": str(BOARD_JSON.name),
            "score": score,
            "mismatch_cells": [
                {
                    "pos": cd["pos"],
                    "row": cd["row"],
                    "col": cd["col"],
                    "current": list(cd["current"]),
                    "current_match": cd["current_match"],
                    "max_possible": cd["max_possible"],
                    "max_match_achievable": cd["max_match_achievable"],
                    "improvement": cd["improvement"],
                    "best_options_count": cd["best_count"],
                    "constraints": cd["constraints"],
                }
                for cd in cell_data
            ],
            "components": [[int(p) for p in c] for c in components],
        }, f, indent=2)
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
