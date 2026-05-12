#!/usr/bin/env python3
"""Interior-first blob: place the highest-tileability interior pieces
in the strain-core region first, before any border CP.

Region: cells at L1 distance <= R from (7,8), the asymmetric hint.
R = 4 gives 41 cells; R = 5 gives 61 cells; R = 6 gives 85 cells.

Approach:
 1. Pin piece 138 at (7,8) rot=0 (hint).
 2. Restrict the available bag to: the 4 hint pieces (138, 180, 207,
    248, 254) FIXED at their official positions; the top-K interior
    pieces by Verhaard tileability ranking AS CANDIDATES for the
    other blob cells.
 3. Backtracking CP with edge-color match constraints among blob cells.
 4. External (blob-boundary) edges are unconstrained.
 5. Maximize internal matched edges in the blob.

The point isn't to solve the full puzzle here — it's to find
whether the strain-core region can reach 0 internal mismatches
when we choose pieces purposefully.
"""

import json
import sys
import time
from pathlib import Path

BORDER = 65535
PUZZLE = Path(__file__).parent.parent.parent / "data" / "puzzles" / "size_16_official_eternity.csv"
HINT_POS = [(7, 8), (2, 13), (2, 2), (13, 13), (13, 2)]  # (x,y) on board
HINT_PID = [138, 180, 207, 248, 254]
HINT_ROT = [0, 1, 1, 2, 1]


def parse_color(s):
    v = int(s.strip(), 2)
    return -1 if v == BORDER else v


def load_pieces():
    pieces = []
    with PUZZLE.open() as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    for ln in lines[1:]:
        cols = ln.split(",")
        top, right, bottom, left = (parse_color(c) for c in cols[:4])
        pieces.append((top, right, bottom, left))
    return pieces


def rotate(piece, rot):
    t, r, b, l = piece
    if rot == 0:
        return (t, r, b, l)
    if rot == 1:
        return (l, t, r, b)
    if rot == 2:
        return (b, l, t, r)
    if rot == 3:
        return (r, b, l, t)


def piece_class(piece):
    borders = sum(1 for c in piece if c == -1)
    if borders == 2: return "corner"
    if borders == 1: return "edge"
    if borders == 0: return "interior"
    return "??"


def main():
    pieces = load_pieces()
    n = len(pieces)
    val = json.load(open("scripts/verhaard_valuation_output.json"))
    tileability = val["tileability"]

    # Sort interior pieces by descending tileability
    interior_pids_sorted = sorted(
        [pid for pid in range(n) if piece_class(pieces[pid]) == "interior"],
        key=lambda pid: -tileability[pid]
    )
    print(f"interior pieces: {len(interior_pids_sorted)}")

    # Blob radius
    HX, HY = 7, 8

    def in_blob(x, y, R):
        return abs(x - HX) + abs(y - HY) <= R

    def gen_blob_cells(R):
        cells = []
        for y in range(0, 16):
            for x in range(0, 16):
                if in_blob(x, y, R):
                    cells.append((x, y))
        return cells

    # CP: place interior pieces in blob cells, respecting hints, with
    # edge-color matching to placed neighbors. Maximize matched edges.

    # Build piece-rotation candidate index: for given (top_req, left_req)
    # where -1 = unconstrained, return list of (pid, rot) candidates.
    # Top/left can be None (unconstrained) or a specific color.
    # We index by (top, left) tuple.

    # Note: blob cells include the hint at (7,8). Other hints at corners
    # are OUTSIDE the blob (since their L1 dist is 12+).

    def cand_pid_rot_for(top_req, left_req, bottom_req, right_req, used):
        """Return list of (pid, rot) candidates whose rotated edges match
        the (potentially None) required colors and that aren't used yet.

        For interior cells: piece must be interior (no border edges).
        """
        cands = []
        for pid in interior_pids_sorted:
            if pid in used:
                continue
            for rot in range(4):
                t, r, b, l = rotate(pieces[pid], rot)
                # interior cells must not have BORDER edges
                if -1 in (t, r, b, l):
                    continue
                if top_req is not None and t != top_req:
                    continue
                if left_req is not None and l != left_req:
                    continue
                if bottom_req is not None and b != bottom_req:
                    continue
                if right_req is not None and r != right_req:
                    continue
                cands.append((pid, rot))
        return cands

    # The hint at (7,8) is piece 138 rot 0.
    # We need its 4 edges to constrain neighbors.
    hint_idx = HINT_PID.index(138)
    hpid, hrot = HINT_PID[hint_idx], HINT_ROT[hint_idx]
    h_t, h_r, h_b, h_l = rotate(pieces[hpid], hrot)
    print(f"hint (7,8) piece {hpid} rot {hrot}: top={h_t} right={h_r} bottom={h_b} left={h_l}")

    # Run a CP-style search on blob cells with backtracking.
    # Order: by L1 distance from (7,8) ascending, then row-major.

    for R in [3, 4, 5]:
        blob = gen_blob_cells(R)
        # Sort blob cells: hint first; then by L1 ascending
        blob.sort(key=lambda xy: (abs(xy[0]-HX) + abs(xy[1]-HY), xy[1], xy[0]))
        print(f"\n=== blob R={R}: {len(blob)} cells ===")

        # placed[(x,y)] = (pid, rot, edges) OR None
        placed = {}
        # Pin hints inside blob
        for (hx, hy), hp, hr in zip(HINT_POS, HINT_PID, HINT_ROT):
            if in_blob(hx, hy, R):
                placed[(hx, hy)] = (hp, hr, rotate(pieces[hp], hr))
        used = set(pid for (pid, _, _) in placed.values())

        def get_neighbor_constraint(x, y):
            """Return (top_req, left_req, bottom_req, right_req) given
            already-placed neighbors. None for unconstrained sides
            (which are either blob-boundary or unfilled blob cell)."""
            top = left = bottom = right = None
            for dx, dy, side in [(0, -1, "top"), (-1, 0, "left"),
                                 (0, 1, "bottom"), (1, 0, "right")]:
                nx, ny = x+dx, y+dy
                if (nx, ny) in placed:
                    np = placed[(nx, ny)]
                    nt, nr, nb, nl = np[2]
                    if side == "top": top = nb
                    elif side == "left": left = nr
                    elif side == "bottom": bottom = nt
                    elif side == "right": right = nl
            return top, left, bottom, right

        # Sequential CP with backtracking.
        # For each unplaced blob cell, find candidates, try them in order
        # of highest tileability; if no candidate, backtrack.
        order = [c for c in blob if c not in placed]
        # Sort cells: place high-constraint cells (cells with 2+ placed
        # neighbors) first.

        deadline = time.time() + 30.0
        max_score = 0
        best_solution = None

        # Simple greedy: at each step, place the most-constrained unplaced cell.
        # No full backtracking — just greedy for fast signal first.

        result_placed = dict(placed)
        result_used = set(used)
        node_count = 0
        success = False

        def greedy_fill():
            nonlocal node_count
            remaining = [c for c in blob if c not in result_placed]
            while remaining:
                node_count += 1
                # Pick the unfilled cell with the most placed neighbors;
                # break ties by L1 distance from hint ascending.
                def cell_priority(cell):
                    x, y = cell
                    nb = 0
                    for dx, dy in [(0,-1),(-1,0),(0,1),(1,0)]:
                        if (x+dx, y+dy) in result_placed:
                            nb += 1
                    return (-nb, abs(x-HX) + abs(y-HY), y, x)
                remaining.sort(key=cell_priority)
                cell = remaining[0]
                x, y = cell
                top, left, bottom, right = get_neighbor_constraint(x, y)
                cands = cand_pid_rot_for(top, left, bottom, right, result_used)
                if not cands:
                    return False
                # Pick the highest-tileability candidate
                best_pid, best_rot = cands[0]
                result_placed[cell] = (best_pid, best_rot, rotate(pieces[best_pid], best_rot))
                result_used.add(best_pid)
                remaining.remove(cell)
            return True

        ok = greedy_fill()
        # Score internal edges of the blob
        internal_edges = 0
        max_internal = 0
        for (x, y), (pid, rot, edges) in result_placed.items():
            t, r, b, l = edges
            # right neighbor in blob?
            if (x+1, y) in result_placed:
                max_internal += 1
                _, _, ne = result_placed[(x+1, y)]
                if r == ne[3]:
                    internal_edges += 1
            # bottom neighbor in blob?
            if (x, y+1) in result_placed:
                max_internal += 1
                _, _, ne = result_placed[(x, y+1)]
                if b == ne[0]:
                    internal_edges += 1
        print(f"  greedy result: ok={ok}, internal_edges={internal_edges}/{max_internal}, nodes={node_count}")
        if ok:
            mm = max_internal - internal_edges
            print(f"  blob mismatches: {mm}")


if __name__ == "__main__":
    main()
