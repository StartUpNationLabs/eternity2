#!/usr/bin/env python3
"""Skeleton + sub-puzzle solver.

Given a top-border-family corpus of 38 boards (all with same border
configuration), extract:
  - Skeleton: 224 cells (5 hints + 60 border + 159 interior consensus).
  - Free zone: 32 cells around the asymmetric hint (7,8).
  - Free pieces: the 32 piece IDs not used in the skeleton.

Then solve the 32-cell sub-puzzle:
  - Assign each free piece to a free cell.
  - Choose a rotation per assignment.
  - Maximize matched edges between free cells AND between free and
    skeleton cells.

Approach: branch-and-bound with constraint propagation. For each
free cell, its piece-rotation domain is filtered by:
  - Boundary-edge constraints (sides facing skeleton must match).
  - All-different on piece IDs.

Score = matched interior edges (just like full puzzle).
We want to MAXIMIZE score. Lower bound = current corpus best (453).
Upper bound on free-zone contribution = (interior edges in free zone).
Total score = (skeleton-matched edges) + (free-matched edges).

For the top family, the skeleton matched-edge count is constant.
So maximizing total = maximizing free-zone matched edges.

This is a focused CSP/MaxSAT instance. ~32 vars × ~10 candidates each.
Should be tractable.
"""

import glob
import json
import sys
from collections import Counter, defaultdict


W = 16
H = 16
BORDER = 0


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0
    return v


def load_pieces(path):
    pieces = []
    with open(path) as f:
        size = int(f.readline().strip())
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            pieces.append(tuple(parse_csv_piece_word(cols[i]) for i in range(4)))
    return pieces


def rotate_quad(q, rot):
    t, r, b, l = q
    if rot == 0: return (t, r, b, l)
    if rot == 1: return (l, t, r, b)
    if rot == 2: return (b, l, t, r)
    if rot == 3: return (r, b, l, t)


def load_corpus_filtered(min_score=449):
    boards = []
    for path in sorted(glob.glob('output/archive/*.json') + glob.glob('output/*.json')):
        try: j = json.load(open(path))
        except: continue
        if not isinstance(j, dict): continue
        sc = j.get('score', {})
        if isinstance(sc, int): score = sc
        elif isinstance(sc, dict): score = sc.get('matched_edges', 0)
        else: continue
        if score < min_score: continue
        if not j.get('placement'): continue
        pl = j['placement']
        if len(pl) != W*H: continue
        boards.append({'path': path, 'score': score, 'pl': pl})
    return boards


def border_sig(pl):
    sig = []
    for ci in range(W*H):
        x, y = ci % W, ci // W
        if x == 0 or x == W-1 or y == 0 or y == W-1:
            c = pl[ci]
            sig.append(c['piece_id'] if c else -1)
    return tuple(sig)


def extract_skeleton(top_boards, consensus_threshold=0.8):
    """For each cell, find the modal piece across top_boards.
    Cells with ≥ consensus_threshold are skeleton; rest are free.

    Returns:
      skeleton: dict cell_idx -> (pid, rot)  (the most common (pid,rot))
      free_cells: list of cell indices.
    """
    skeleton = {}
    free_cells = []
    cell_data = defaultdict(Counter)
    for b in top_boards:
        for ci, c in enumerate(b['pl']):
            if c is not None:
                cell_data[ci][(c['piece_id'], c['rotation'])] += 1
    for ci in range(W*H):
        items = cell_data[ci]
        if not items:
            free_cells.append(ci)
            continue
        modal, modal_n = items.most_common(1)[0]
        total = sum(items.values())
        if modal_n / total >= consensus_threshold:
            skeleton[ci] = modal
        else:
            free_cells.append(ci)
    return skeleton, free_cells


def neighbour_color(skeleton, pieces, cell_idx, side):
    """Color presented by the neighbour of cell_idx on `side` IF
    that neighbour is skeleton. Returns None if neighbour is free
    or off-board.

    side: 0=top, 1=right, 2=bottom, 3=left
    Returns the color the NEIGHBOUR shows on its facing side
    (= what our piece must match on its `side`).
    """
    x, y = cell_idx % W, cell_idx // W
    if side == 0:
        if y == 0: return BORDER
        nc = (y-1)*W+x; opp = 2
    elif side == 1:
        if x == W-1: return BORDER
        nc = y*W+x+1; opp = 3
    elif side == 2:
        if y == H-1: return BORDER
        nc = (y+1)*W+x; opp = 0
    else:
        if x == 0: return BORDER
        nc = y*W+x-1; opp = 1
    if nc not in skeleton:
        return None
    pid, rot = skeleton[nc]
    return rotate_quad(pieces[pid], rot)[opp]


def filter_candidates(pieces, free_pids, cell_idx, skeleton):
    """For a free cell, return list of (pid, rot) tuples that match
    the skeleton-fixed neighbour constraints. (Other free neighbours
    add no constraint here; they'll be enforced during search.)"""
    constraints = {}
    for side in range(4):
        c = neighbour_color(skeleton, pieces, cell_idx, side)
        if c is not None:
            constraints[side] = c
    cands = []
    for pid in free_pids:
        for rot in range(4):
            edges = rotate_quad(pieces[pid], rot)
            ok = all(edges[s] == constraints[s] for s in constraints)
            if ok:
                cands.append((pid, rot))
    return cands


def free_zone_edges(free_cells, skeleton):
    """Return list of (cell_a, side_a, cell_b, side_b) for edges
    BETWEEN two free cells, plus list of (cell, side, required_color)
    for edges between free cells and skeleton (already encoded by
    candidate filtering, but we also count these in the score).
    """
    free_set = set(free_cells)
    free_free_edges = []
    free_skel_edges = []
    for ci in free_cells:
        x, y = ci % W, ci // W
        for side, (dx, dy, opp) in enumerate([(0,-1,2), (1,0,3), (0,1,0), (-1,0,1)]):
            nx, ny = x+dx, y+dy
            if 0 <= nx < W and 0 <= ny < H:
                nc = ny*W+nx
                if ci < nc:  # avoid double count
                    if nc in free_set:
                        free_free_edges.append((ci, side, nc, opp))
    return free_free_edges


def main():
    pieces = load_pieces('../data/puzzles/size_16_official_eternity.csv')
    boards = load_corpus_filtered(min_score=449)
    print(f"# corpus ≥449 with placement: {len(boards)}")

    sig_counts = Counter()
    for b in boards: sig_counts[border_sig(b['pl'])] += 1
    top_sig, top_n = sig_counts.most_common(1)[0]
    top_boards = [b for b in boards if border_sig(b['pl']) == top_sig]
    print(f"# top border family: {top_n} boards")

    skeleton, free_cells = extract_skeleton(top_boards, consensus_threshold=0.8)
    print(f"# skeleton cells: {len(skeleton)}")
    print(f"# free cells: {len(free_cells)}")

    # Free piece pool = all pieces not in skeleton.
    used_pids = set(p[0] for p in skeleton.values())
    free_pids = sorted(set(range(len(pieces))) - used_pids)
    print(f"# free pieces: {len(free_pids)}  (matches free cells: {len(free_pids) == len(free_cells)})")

    # Per free cell: candidate (pid, rot) tuples filtered by skeleton constraints.
    cell_candidates = {}
    for ci in free_cells:
        cell_candidates[ci] = filter_candidates(pieces, free_pids, ci, skeleton)
    cand_sizes = sorted([len(cs) for cs in cell_candidates.values()])
    print(f"# candidate counts per free cell: min={cand_sizes[0]} median={cand_sizes[len(cand_sizes)//2]} max={cand_sizes[-1]}")
    print(f"# total per-cell pre-product: {sum(cand_sizes)} (= upper bound on branching at root)")

    # Internal free-free edges.
    ff_edges = free_zone_edges(free_cells, skeleton)
    print(f"# internal free-free edges: {len(ff_edges)}")
    print(f"# (each must MATCH for a perfect free-zone solution)")

    # Compute current best score from one of the 453 boards in the family.
    boards_453 = [b for b in top_boards if b['score'] == 453]
    if boards_453:
        # Sanity: how many free-zone edges match in the existing 453?
        b = boards_453[0]
        from_pl = b['pl']
        # Build current placement quads for free cells.
        n_free_match = 0
        for (ca, sa, cb, sb) in ff_edges:
            pa, ra = from_pl[ca]['piece_id'], from_pl[ca]['rotation']
            pb, rb = from_pl[cb]['piece_id'], from_pl[cb]['rotation']
            ea = rotate_quad(pieces[pa], ra)[sa]
            eb = rotate_quad(pieces[pb], rb)[sb]
            if ea == eb and ea != BORDER:
                n_free_match += 1
        print(f"\n# baseline 453 board: free-zone internal matches = {n_free_match}/{len(ff_edges)}")
        print(f"# baseline 453 board: free-zone defects = {len(ff_edges) - n_free_match}")

        # Skeleton-edge matches (free cell <-> skeleton cell).
        n_skel_match = 0
        n_skel_total = 0
        for ci in free_cells:
            x, y = ci % W, ci // W
            cell_pid, cell_rot = from_pl[ci]['piece_id'], from_pl[ci]['rotation']
            cell_edges = rotate_quad(pieces[cell_pid], cell_rot)
            for side, (dx, dy, opp) in enumerate([(0,-1,2), (1,0,3), (0,1,0), (-1,0,1)]):
                nx, ny = x+dx, y+dy
                if 0 <= nx < W and 0 <= ny < H:
                    nc = ny*W+nx
                    if nc in skeleton:
                        skel_pid, skel_rot = skeleton[nc]
                        skel_edge = rotate_quad(pieces[skel_pid], skel_rot)[opp]
                        n_skel_total += 1
                        if cell_edges[side] == skel_edge and cell_edges[side] != BORDER:
                            n_skel_match += 1
        print(f"# baseline 453 board: free→skeleton edge matches = {n_skel_match}/{n_skel_total}")

    # Save the sub-puzzle metadata for downstream solver.
    out = {
        'free_cells': free_cells,
        'free_pids': free_pids,
        'skeleton': {str(ci): list(skeleton[ci]) for ci in skeleton},
        'cell_candidates': {str(ci): cell_candidates[ci] for ci in free_cells},
        'free_free_edges': ff_edges,
        'border_sig_size': len(top_sig),
        'corpus_size': top_n,
    }
    with open('output/skeleton_subpuzzle.json', 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# wrote output/skeleton_subpuzzle.json")


if __name__ == "__main__":
    main()
