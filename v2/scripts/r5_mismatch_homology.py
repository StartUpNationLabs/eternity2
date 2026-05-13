#!/usr/bin/env python3
# R5 — mismatch homology on saved E2 boards.
#
# For each saved board JSON (with "placement" array), compute:
#   - placed count, matched count (re-derived from the CSV)
#   - mismatch graph: cells with at least one mismatched edge are
#     vertices; cell adjacency through a MATCHED edge connects two
#     vertices (we want to study the topology of the *mismatch region*
#     as it sits embedded in the grid).
#   - actually two complementary views — pick the one that's a homology
#     question:
#
#   View A (mismatch-edge graph):
#     vertices = cells touching a mismatch.
#     edges    = mismatched cell-cell adjacencies (between two cells
#                that share a mismatched edge).
#     β_0 = # connected components.
#     β_1 = # independent cycles = |E| - |V| + β_0.
#
#   View B (mismatch-region planar dual):
#     vertices = cells in the mismatch region (where region = union of
#                cells incident to at least one mismatch).
#     edges    = any cell adjacency between two region cells (regardless
#                of edge match/mismatch). β_1 of this captures "holes"
#                in the contiguous mismatch region (whether perfect
#                cells are surrounded by mismatched ones).
#
# Both views are linear-algebra easy: β_1 = E - V + C for a graph.
# We compute both per board.

import csv
import json
import math
import os
import re
import sys
from pathlib import Path
from collections import defaultdict, deque

V2_ROOT = Path(__file__).resolve().parents[1]
PUZZLE_CSV = V2_ROOT.parent / "data/puzzles/size_16_official_eternity.csv"

BORDER = 255

# direction encoding: 0=N, 1=E, 2=S, 3=W
DIR_DX = (0, 1, 0, -1)
DIR_DY = (-1, 0, 1, 0)

def parse_color(bits16: str) -> int:
    v = int(bits16, 2)
    return BORDER if v == 65535 else v

def load_puzzle(path: Path):
    pieces = []
    size = 0
    with path.open() as f:
        for row in csv.reader(f):
            if len(row) == 0:
                continue
            if len(row) < 4:
                size = int(row[0])
                continue
            n = parse_color(row[0])
            e = parse_color(row[1])
            s = parse_color(row[2])
            w = parse_color(row[3])
            pieces.append((n, e, s, w))
    return size, pieces

def piece_after_rotation(piece, rot: int):
    # rot ∈ {0,1,2,3}: 0=identity, 1=CW90, 2=180, 3=CCW90.
    # Board API: rotation k means cardinal sides shift by k positions cyclically.
    # We need to know, for a placed piece, what color sits on the N/E/S/W side
    # of the board cell after rotation. We assume the convention used in
    # core::Rotation::apply: side[k after rotation r] = piece[(k - r) mod 4]
    # where sides are indexed (N=0, E=1, S=2, W=3). This is the standard
    # CW-rotation interpretation. We'll verify by sanity-checking match
    # counts against the saved JSON "matched" field.
    n = piece[(0 - rot) % 4]
    e = piece[(1 - rot) % 4]
    s = piece[(2 - rot) % 4]
    w = piece[(3 - rot) % 4]
    return n, e, s, w

def load_placement(json_path: Path, size: int):
    with json_path.open() as f:
        d = json.load(f)
    placement = d.get("placement")
    if placement is None:
        return None, d
    # placement is a length-(size*size) array; entries are either null
    # or {"pos": p, "piece_id": pid, "rotation": r}.
    board = [None] * (size * size)
    for entry in placement:
        if entry is None:
            continue
        pos = int(entry["pos"])
        pid = int(entry["piece_id"])
        rot = int(entry["rotation"])
        board[pos] = (pid, rot)
    return board, d

def score_and_classify_edges(board, size, pieces):
    # Returns (matched, total_placed_edges, mismatched_edges_set).
    # An edge is a pair (cell_a, cell_b) with cell_a < cell_b, both placed,
    # adjacent on the grid. mismatched = colors differ on the shared side.
    matched = 0
    mismatched = set()
    # iterate over horizontal and vertical edges
    for y in range(size):
        for x in range(size):
            pos = y * size + x
            if board[pos] is None:
                continue
            pid, rot = board[pos]
            n, e, s, w = piece_after_rotation(pieces[pid], rot)
            # eastward neighbor
            if x + 1 < size:
                npos = pos + 1
                if board[npos] is not None:
                    npid, nrot = board[npos]
                    _, _, _, nw = piece_after_rotation(pieces[npid], nrot)
                    if e == nw:
                        matched += 1
                    else:
                        a, b = min(pos, npos), max(pos, npos)
                        mismatched.add((a, b))
            # southward neighbor
            if y + 1 < size:
                npos = pos + size
                if board[npos] is not None:
                    npid, nrot = board[npos]
                    nn, _, _, _ = piece_after_rotation(pieces[npid], nrot)
                    if s == nn:
                        matched += 1
                    else:
                        a, b = min(pos, npos), max(pos, npos)
                        mismatched.add((a, b))
    return matched, mismatched

def connected_components(vertices, edges):
    adj = defaultdict(set)
    for v in vertices:
        adj[v]  # ensure key
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    seen = set()
    comps = []
    for v in vertices:
        if v in seen:
            continue
        comp = []
        q = deque([v])
        seen.add(v)
        while q:
            u = q.popleft()
            comp.append(u)
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    q.append(w)
        comps.append(comp)
    return comps

def compute_betti(vertices, edges):
    # β_0 = # components
    # β_1 = |E| - |V| + β_0  (for a connected piece of graph β_1 = |E| - |V| + 1)
    if not vertices:
        return (0, 0)
    comps = connected_components(vertices, edges)
    b0 = len(comps)
    b1 = len(edges) - len(vertices) + b0
    return (b0, b1)

def view_a_mismatch_edge_graph(size, mismatched):
    # vertices = cells touching a mismatched edge
    vertices = set()
    for a, b in mismatched:
        vertices.add(a)
        vertices.add(b)
    edges = set(mismatched)
    return vertices, edges

def view_b_mismatch_region_graph(size, mismatched):
    # vertices = cells touching at least one mismatched edge
    # edges = ALL cell adjacencies between two such cells, regardless of match
    region = set()
    for a, b in mismatched:
        region.add(a)
        region.add(b)
    edges = set()
    for v in region:
        x, y = v % size, v // size
        for dx, dy in [(1, 0), (0, 1)]:  # only right/down to avoid double-counting
            nx, ny = x + dx, y + dy
            if 0 <= nx < size and 0 <= ny < size:
                n = ny * size + nx
                if n in region:
                    edges.add((v, n))
    return region, edges

def view_c_mismatch_cells_through_match(size, board, mismatched):
    # vertices = cells with at least one mismatched edge
    # edges = adjacencies between two such cells where the edge is MATCHED
    # (i.e., the cells are connected by a "good" bridge inside the bad region).
    # β_1 measures cycles formed by good edges inside the bad region.
    region = set()
    for a, b in mismatched:
        region.add(a)
        region.add(b)
    placed_cells = set(i for i in range(size * size) if board[i] is not None)
    edges = set()
    for v in region:
        x, y = v % size, v // size
        for dx, dy in [(1, 0), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < size and 0 <= ny < size:
                n = ny * size + nx
                if n in region:
                    if (v, n) not in mismatched and (n, v) not in mismatched:
                        # both endpoints placed (guaranteed by region) and edge is matched
                        edges.add((v, n))
    return region, edges

def interior_perfect_islands(size: int, board, region: set) -> list:
    # Return the list of connected components of (all cells \ region) that
    # do NOT touch the puzzle boundary (i.e., interior "holes" in region).
    # Cells outside the board are treated as "outside the universe" — a
    # component is "interior" iff none of its cells is on row 0/15 or col 0/15.
    placed = set(i for i in range(size * size) if board[i] is not None)
    # complement universe: all placed cells not in region
    universe = placed - region
    seen = set()
    interior_components = []
    for v in universe:
        if v in seen:
            continue
        comp = []
        touches_boundary = False
        q = deque([v])
        seen.add(v)
        while q:
            u = q.popleft()
            comp.append(u)
            x, y = u % size, u // size
            if x == 0 or x == size - 1 or y == 0 or y == size - 1:
                touches_boundary = True
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < size and 0 <= ny < size:
                    n = ny * size + nx
                    if n in universe and n not in seen:
                        seen.add(n)
                        q.append(n)
        if not touches_boundary:
            interior_components.append(comp)
    return interior_components

def board_summary(json_path: Path, size: int, pieces):
    board, meta = load_placement(json_path, size)
    if board is None:
        return None
    placed = sum(1 for c in board if c is not None)
    matched, mismatched = score_and_classify_edges(board, size, pieces)
    declared = meta.get("matched") or meta.get("matched_alns") or meta.get("matched_best")
    # View A
    vA, eA = view_a_mismatch_edge_graph(size, mismatched)
    b0_A, b1_A = compute_betti(vA, eA)
    # View B
    vB, eB = view_b_mismatch_region_graph(size, mismatched)
    b0_B, b1_B = compute_betti(vB, eB)
    # View C
    vC, eC = view_c_mismatch_cells_through_match(size, board, mismatched)
    b0_C, b1_C = compute_betti(vC, eC)
    # Interior perfect islands (the actionable view-B holes)
    islands = interior_perfect_islands(size, board, vB)
    island_sizes = sorted([len(c) for c in islands], reverse=True)
    return {
        "path": str(json_path.relative_to(V2_ROOT)),
        "placed": placed,
        "matched_computed": matched,
        "matched_declared": declared,
        "mismatch_edges": len(mismatched),
        # View A: mismatch-edge graph (just the bad edges)
        "A_vertices": len(vA),
        "A_edges": len(eA),
        "A_components": b0_A,
        "A_beta1": b1_A,
        # View B: mismatch-region graph (all adjacencies within bad cells)
        "B_vertices": len(vB),
        "B_edges": len(eB),
        "B_components": b0_B,
        "B_beta1": b1_B,
        # View C: matched-bridges inside the bad region
        "C_vertices": len(vC),
        "C_edges": len(eC),
        "C_components": b0_C,
        "C_beta1": b1_C,
        "interior_islands": len(islands),
        "island_sizes": island_sizes,
        "interior_island_cells": sum(island_sizes),
    }

def main():
    size, pieces = load_puzzle(PUZZLE_CSV)
    print(f"# loaded puzzle: size={size}, {len(pieces)} pieces")
    if len(sys.argv) < 2:
        print("usage: r5_mismatch_homology.py <board.json> [board.json ...]")
        sys.exit(1)
    print()
    print("path | placed | matched(comp) | matched(decl) | mismE | A:V/E/C/β1 | B:V/E/C/β1 | C:V/E/C/β1")
    print("-" * 130)
    rows = []
    for arg in sys.argv[1:]:
        p = Path(arg).resolve()
        s = board_summary(p, size, pieces)
        if s is None:
            print(f"  {p}: no placement, skipped")
            continue
        rows.append(s)
        short = s["path"]
        if len(short) > 55:
            short = "..." + short[-52:]
        print(
            f"{short} | {s['placed']:>3} | {s['matched_computed']:>3} | "
            f"{str(s['matched_declared']):>3} | {s['mismatch_edges']:>3} | "
            f"{s['A_vertices']:>3}/{s['A_edges']:>3}/{s['A_components']:>2}/{s['A_beta1']:>3} | "
            f"{s['B_vertices']:>3}/{s['B_edges']:>3}/{s['B_components']:>2}/{s['B_beta1']:>3} | "
            f"{s['C_vertices']:>3}/{s['C_edges']:>3}/{s['C_components']:>2}/{s['C_beta1']:>3}"
        )

    if rows:
        print()
        print("## Summary across boards")
        print(f"  N boards     : {len(rows)}")
        # Verify score recomputation matches declared
        mismatches_decl = sum(1 for r in rows if r["matched_declared"] is not None and r["matched_computed"] != r["matched_declared"])
        print(f"  score parity : {len(rows) - mismatches_decl}/{len(rows)} match declared (rotation convention check)")
        for view in ["A", "B", "C"]:
            b1s = [r[f"{view}_beta1"] for r in rows]
            b0s = [r[f"{view}_components"] for r in rows]
            print(f"  View {view}: β_0 range={min(b0s)}-{max(b0s)}, β_1 range={min(b1s)}-{max(b1s)}, β_1 mean={sum(b1s)/len(b1s):.2f}")
        print()
        print("## Interior perfect islands (cells in R^c not touching board boundary)")
        print("path | matched | islands | total_cells | sizes (top)")
        for r in rows:
            short = r["path"]
            if len(short) > 55: short = "..." + short[-52:]
            tops = ",".join(str(x) for x in r["island_sizes"][:8])
            print(f"  {short} | {r['matched_computed']:>3} | {r['interior_islands']:>2} | {r['interior_island_cells']:>3} | {tops}")
        # Verify the hypothesis: View B β_1 == # interior islands
        print()
        match = sum(1 for r in rows if r["B_beta1"] == r["interior_islands"])
        print(f"  View-B β_1 == interior-island count: {match}/{len(rows)} boards")

if __name__ == "__main__":
    main()
