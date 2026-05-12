#!/usr/bin/env python3
"""Backtracking solver for the free-zone sub-puzzle.

Given a skeleton + free cells + free pieces, search for the placement
of free pieces that maximizes matched edges.

Approach:
- MRV (minimum remaining values) variable ordering.
- LCV (least constraining value) for value ordering.
- Forward checking: when a piece is placed, prune candidates from
  neighbouring free cells.
- Branch-and-bound with best-found-so-far as lower bound.

For ~32-82 free cells with 5-100 candidates each, careful branching
should find the optimum or a near-optimum in minutes.
"""

import argparse
import json
import sys
import time
from collections import defaultdict


W = 16; H = 16; BORDER = 0


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535: return 0
    return v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4: continue
            pieces.append(tuple(parse_csv_piece_word(cols[i]) for i in range(4)))
    return pieces


def rotate_quad(q, rot):
    t, r, b, l = q
    if rot == 0: return (t, r, b, l)
    if rot == 1: return (l, t, r, b)
    if rot == 2: return (b, l, t, r)
    if rot == 3: return (r, b, l, t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subpuzzle', default='output/skeleton_subpuzzle.json')
    ap.add_argument('--puzzle', default='../data/puzzles/size_16_official_eternity.csv')
    ap.add_argument('--time-budget', type=int, default=600)
    ap.add_argument('--out', default='output/free_zone_best.json')
    args = ap.parse_args()

    pieces = load_pieces(args.puzzle)
    sp = json.load(open(args.subpuzzle))
    free_cells = sp['free_cells']
    free_pids = sp['free_pids']
    skeleton = {int(k): tuple(v) for k, v in sp['skeleton'].items()}
    cell_candidates = {int(k): [tuple(c) for c in v] for k, v in sp['cell_candidates'].items()}
    ff_edges = [tuple(e) for e in sp['free_free_edges']]

    print(f'free cells: {len(free_cells)}', file=sys.stderr)
    print(f'free pieces: {len(free_pids)}', file=sys.stderr)
    print(f'free-free edges: {len(ff_edges)}', file=sys.stderr)

    # Precompute piece-rotation edge lookup.
    piece_edges = {}
    for pid in free_pids:
        for rot in range(4):
            piece_edges[(pid, rot)] = rotate_quad(pieces[pid], rot)

    # Build adjacency: for each free cell, which other free cells are neighbours?
    free_set = set(free_cells)
    cell_neighbours = {}
    for ci in free_cells:
        x, y = ci % W, ci // W
        nbs = {}
        for side, (dx, dy, opp) in enumerate([(0,-1,2), (1,0,3), (0,1,0), (-1,0,1)]):
            nx, ny = x+dx, y+dy
            if 0 <= nx < W and 0 <= ny < H:
                nc = ny*W+nx
                if nc in free_set:
                    nbs[side] = (nc, opp)
        cell_neighbours[ci] = nbs

    # Precompute skeleton-edge match count per cell+piece+rotation.
    # That's the number of edges this (cell, pid, rot) matches against
    # skeleton neighbours.
    skel_match = {}
    for ci in free_cells:
        x, y = ci % W, ci // W
        for (pid, rot) in cell_candidates[ci]:
            edges = piece_edges[(pid, rot)]
            n = 0
            for side, (dx, dy, opp) in enumerate([(0,-1,2), (1,0,3), (0,1,0), (-1,0,1)]):
                nx, ny = x+dx, y+dy
                if 0 <= nx < W and 0 <= ny < H:
                    nc = ny*W+nx
                    if nc in skeleton:
                        skel_pid, skel_rot = skeleton[nc]
                        skel_color = rotate_quad(pieces[skel_pid], skel_rot)[opp]
                        if edges[side] == skel_color and edges[side] != BORDER:
                            n += 1
            skel_match[(ci, pid, rot)] = n

    # Skeleton-only baseline: how many internal edges does the skeleton
    # already match?
    skel_internal = 0
    skel_set = set(skeleton.keys())
    for ci in skel_set:
        x, y = ci % W, ci // W
        pid, rot = skeleton[ci]
        edges = rotate_quad(pieces[pid], rot)
        # Count right + bottom edges to avoid double-count.
        if x+1 < W and (y*W+x+1) in skel_set:
            spid, srot = skeleton[y*W+x+1]
            sedges = rotate_quad(pieces[spid], srot)
            if edges[1] == sedges[3] and edges[1] != BORDER:
                skel_internal += 1
        if y+1 < H and ((y+1)*W+x) in skel_set:
            spid, srot = skeleton[(y+1)*W+x]
            sedges = rotate_quad(pieces[spid], srot)
            if edges[2] == sedges[0] and edges[2] != BORDER:
                skel_internal += 1
    print(f'skeleton internal matched edges: {skel_internal}', file=sys.stderr)

    # State: cur_assignment[ci] = (pid, rot), used_pids = set.
    # To compute score: skel_internal + sum(skel_match for placed cells)
    # + count(matched ff_edges that are now internal-resolvable).

    cur = {}  # cell_idx -> (pid, rot)
    used = set()
    best_score = skel_internal
    best_assignment = {}
    deadline = time.time() + args.time_budget
    nodes_visited = [0]

    # Precompute order: pick free cells with FEWEST candidates first.
    # But SKIP cells with 0 candidates — fill them greedily at end.
    leftover_cells = [c for c in free_cells if not cell_candidates[c]]
    searchable_cells = [c for c in free_cells if cell_candidates[c]]
    cells_sorted = sorted(searchable_cells, key=lambda c: len(cell_candidates[c]))
    print(f'searchable cells (≥1 cand): {len(cells_sorted)}', file=sys.stderr)
    print(f'leftover cells (0 cand): {len(leftover_cells)}', file=sys.stderr)

    def evaluate_partial():
        """Return current matched-edge count given cur."""
        s = skel_internal
        # Free→skeleton match contributions.
        for ci, (pid, rot) in cur.items():
            s += skel_match[(ci, pid, rot)]
        # Free→free edges (only count if BOTH endpoints placed).
        for (ca, sa, cb, sb) in ff_edges:
            if ca in cur and cb in cur:
                pa, ra = cur[ca]
                pb, rb = cur[cb]
                ea = piece_edges[(pa, ra)][sa]
                eb = piece_edges[(pb, rb)][sb]
                if ea == eb and ea != BORDER:
                    s += 1
        return s

    def upper_bound():
        """Optimistic remaining-edge bound: assume every remaining
        free cell achieves its max possible skel_match contribution
        AND every remaining ff_edge matches."""
        s = evaluate_partial()
        # Add max possible skel contribution from unplaced cells.
        for ci in cells_sorted:
            if ci in cur: continue
            best_for_cell = 0
            for (pid, rot) in cell_candidates[ci]:
                if pid in used: continue
                m = skel_match[(ci, pid, rot)]
                if m > best_for_cell: best_for_cell = m
            s += best_for_cell
        # Add ff_edges where one or both endpoints not yet placed.
        for (ca, sa, cb, sb) in ff_edges:
            if not (ca in cur and cb in cur):
                s += 1  # optimistic: assume it matches
        return s

    def backtrack(idx):
        nonlocal best_score, best_assignment
        nodes_visited[0] += 1
        if time.time() > deadline:
            return False  # signal time-out
        if idx == len(cells_sorted):
            score = evaluate_partial()
            if score > best_score:
                best_score = score
                best_assignment = dict(cur)
                print(f'  [t={time.time()-start:.0f}s nodes={nodes_visited[0]}] '
                      f'NEW BEST {best_score}', file=sys.stderr)
            return True
        ci = cells_sorted[idx]
        cands = [(pid, rot) for (pid, rot) in cell_candidates[ci] if pid not in used]
        # Order candidates by descending skel_match (LCV-ish heuristic).
        cands.sort(key=lambda c: -skel_match[(ci, c[0], c[1])])
        for (pid, rot) in cands:
            cur[ci] = (pid, rot)
            used.add(pid)
            ub = upper_bound()
            if ub > best_score:
                if not backtrack(idx + 1):
                    del cur[ci]
                    used.discard(pid)
                    return False
            del cur[ci]
            used.discard(pid)
        return True

    print(f'\n=== solving (budget {args.time_budget}s) ===', file=sys.stderr)
    start = time.time()
    backtrack(0)
    elapsed = time.time() - start
    print(f'\n=== done ===', file=sys.stderr)
    print(f'time: {elapsed:.1f}s', file=sys.stderr)
    print(f'nodes visited: {nodes_visited[0]}', file=sys.stderr)
    print(f'best free-zone score (incl skeleton internal): {best_score}', file=sys.stderr)

    # Greedy-fill leftover cells with remaining unused pieces, any rotation.
    if leftover_cells and best_assignment:
        unused = set(free_pids) - set(p for (p, _) in best_assignment.values())
        for ci in leftover_cells:
            if not unused: break
            pid = next(iter(unused))
            best_assignment[ci] = (pid, 0)
            unused.discard(pid)

    # If we have a complete assignment, verify by building the full board.
    if len(best_assignment) >= len(searchable_cells):
        full_pl = [None] * (W*H)
        for ci, (pid, rot) in skeleton.items():
            full_pl[ci] = {'piece_id': int(pid), 'rotation': int(rot)}
        for ci, (pid, rot) in best_assignment.items():
            full_pl[ci] = {'piece_id': int(pid), 'rotation': int(rot)}
        # Compute full score.
        s = 0
        for y in range(H):
            for x in range(W):
                pos = y*W+x
                if not full_pl[pos]: continue
                pid, rot = full_pl[pos]['piece_id'], full_pl[pos]['rotation']
                edges = rotate_quad(pieces[pid], rot)
                if x+1 < W and full_pl[pos+1]:
                    npid, nrot = full_pl[pos+1]['piece_id'], full_pl[pos+1]['rotation']
                    nedges = rotate_quad(pieces[npid], nrot)
                    if edges[1] == nedges[3] and edges[1] != BORDER: s += 1
                if y+1 < H and full_pl[pos+W]:
                    npid, nrot = full_pl[pos+W]['piece_id'], full_pl[pos+W]['rotation']
                    nedges = rotate_quad(pieces[npid], nrot)
                    if edges[2] == nedges[0] and edges[2] != BORDER: s += 1
        print(f'\nfull-board score: {s}/480 (mismatches: {480-s})', file=sys.stderr)
        out = {
            'run_name': 'free_zone_solver',
            'puzzle': {'name': 'size_16_official_eternity'},
            'score': {'matched_edges': s, 'total_edges': 480, 'percent': 100*s/480,
                      'placed_cells': sum(1 for p in full_pl if p), 'total_cells': W*H},
            'placement': full_pl,
        }
        with open(args.out, 'w') as f:
            json.dump(out, f, indent=2)
        print(f'wrote {args.out}', file=sys.stderr)
    else:
        print(f'partial assignment: {len(best_assignment)}/{len(free_cells)} cells placed',
              file=sys.stderr)


if __name__ == '__main__':
    main()
