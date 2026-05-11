#!/usr/bin/env python3
"""Region Optimisation via Max-Clique (Salassa 2017 §3.5 replication).

Given a board with a R×R region freed and the rest pinned, find the
optimal placement of pieces in the region via maximum clique on a
compatibility graph.

Graph definition:
  - Node = (cell, piece, rotation) tuple where:
    * cell is a free cell in the region.
    * piece is an unused piece (not placed outside the region).
    * rotation satisfies the OUTSIDE-boundary color constraints
      (= piece's color on each side facing a pinned cell must
      equal that pinned cell's facing color).
  - Edge between two nodes (c1, p1, r1) and (c2, p2, r2) iff:
    * c1 ≠ c2.
    * p1 ≠ p2.
    * If c1, c2 are adjacent: their facing edges MATCH (= same color).
    * If c1, c2 not adjacent: no constraint beyond piece-uniqueness.

Max clique = largest subset of compatible placements. If max-clique
size equals the number of free cells, the region is perfectly fillable
under the given boundary — replace the region with that placement.

Per Salassa §3.5, this finds an OPTIMAL placement for the region; if
the result improves total edge matches, apply it.

EXPERIMENTAL: Salassa used a custom Grosso-Locatelli-Pullan heuristic
with q=10M selections. We use python-igraph's `largest_cliques()`,
which is Bron-Kerbosch with pivoting — exact, but expensive on dense
graphs. For 5×5 regions (~100-300 nodes) this is fast. For 6×6
(~200-600 nodes) borderline. For 7×7+ too slow.

Usage:
    python3 scripts/region_max_clique.py BOARD_JSON \\
        --region-x X --region-y Y --region-k K [--out OUT]

Reads the board from the canonical placement format. Outputs the
improved board if max-clique was a full region; otherwise reports
the maximum partial fill found.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import igraph as ig

W = 16
H = 16
BORDER = 0
N_CELLS = W * H


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0
    return v


def load_puzzle(path):
    pieces = []
    hints = {}
    with open(path) as f:
        size = int(f.readline().strip())
        assert size == W
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            quad = tuple(parse_csv_piece_word(cols[i]) for i in range(4))
            pieces.append(quad)
            if len(cols) >= 7:
                x = int(cols[4]); y = int(cols[5]); rot = int(cols[6])
                if (x, y, rot) != (0, 0, 0):
                    pos = y * W + x
                    hints[pos] = (pid, rot)
    return np.array(pieces, dtype=np.int32), hints


def piece_rotations_tensor(pieces):
    n = pieces.shape[0]
    out = np.zeros((n, 4, 4), dtype=np.int32)
    out[:, 0, :] = pieces
    out[:, 1, 0] = pieces[:, 3]
    out[:, 1, 1] = pieces[:, 0]
    out[:, 1, 2] = pieces[:, 1]
    out[:, 1, 3] = pieces[:, 2]
    out[:, 2, 0] = pieces[:, 2]
    out[:, 2, 1] = pieces[:, 3]
    out[:, 2, 2] = pieces[:, 0]
    out[:, 2, 3] = pieces[:, 1]
    out[:, 3, 0] = pieces[:, 1]
    out[:, 3, 1] = pieces[:, 2]
    out[:, 3, 2] = pieces[:, 3]
    out[:, 3, 3] = pieces[:, 0]
    return out


def load_board(json_path):
    j = json.load(open(json_path))
    placement = j.get("placement")
    if placement is None:
        raise ValueError(f"no placement in {json_path}")
    board = np.full(N_CELLS, -1, dtype=np.int32)
    for pos, cell in enumerate(placement):
        if cell is None:
            continue
        board[pos] = int(cell["piece_id"]) * 4 + int(cell["rotation"])
    return board, j


def unpack(packed):
    return packed // 4, packed % 4


def pack(pid, rot):
    return pid * 4 + rot


def region_cells(x0, y0, k):
    """Return list of cell positions in the [x0..x0+k) × [y0..y0+k) region."""
    return [(y0 + dy) * W + (x0 + dx) for dy in range(k) for dx in range(k)]


def boundary_color_at(board, piece_rot, cell, side):
    """Color on `side` of the piece at `cell`. side: 0=top, 1=right,
    2=bottom, 3=left. Returns -1 if `cell` is empty."""
    if board[cell] < 0:
        return -1
    pid, rot = unpack(board[cell])
    return int(piece_rot[pid, rot, side])


def outside_color_for(board, piece_rot, free_cells, cell, side):
    """For a free cell, what color does its `side`-side face from outside
    the region?
    side: 0=top, 1=right, 2=bottom, 3=left.
    The opposite side of the neighbor: top neighbor's bottom = my top, etc.
    Returns:
      None if the neighbor is in free_cells (no constraint, internal).
      BORDER (=0) if neighbor is off the board.
      otherwise the color the OUTSIDE neighbor presents.
    """
    x, y = cell % W, cell // W
    if side == 0:
        if y == 0:
            return BORDER
        nbr = (y - 1) * W + x
        opp_side = 2
    elif side == 1:
        if x == W - 1:
            return BORDER
        nbr = y * W + (x + 1)
        opp_side = 3
    elif side == 2:
        if y == H - 1:
            return BORDER
        nbr = (y + 1) * W + x
        opp_side = 0
    else:
        if x == 0:
            return BORDER
        nbr = y * W + (x - 1)
        opp_side = 1
    if nbr in free_cells:
        return None  # internal — no constraint from outside
    if board[nbr] < 0:
        return None  # neighbor empty (shouldn't happen)
    return boundary_color_at(board, piece_rot, nbr, opp_side)


def candidate_nodes(board, piece_rot, free_cells, n_pieces, pinned_pieces_set):
    """For each free cell, enumerate (piece, rotation) candidates that
    are consistent with the OUTSIDE boundary colors.

    Returns list of (cell, pid, rot) tuples, and the set of pieces
    AVAILABLE for the region (= all pieces not pinned outside).
    """
    free_set = set(free_cells)
    available = [p for p in range(n_pieces) if p not in pinned_pieces_set]
    print(f"# {len(available)} available pieces; {len(free_cells)} free cells",
          file=sys.stderr)

    nodes = []
    for cell in free_cells:
        # Required colors on outside-facing sides.
        bdry = {}
        for side in range(4):
            c = outside_color_for(board, piece_rot, free_set, cell, side)
            if c is not None:
                bdry[side] = c

        cell_nodes = 0
        for pid in available:
            for rot in range(4):
                edges = piece_rot[pid, rot]
                ok = True
                for side, req in bdry.items():
                    if int(edges[side]) != int(req):
                        ok = False
                        break
                if not ok:
                    continue
                nodes.append((cell, pid, rot))
                cell_nodes += 1
    return nodes, available


def build_compatibility_graph(nodes, free_cells, piece_rot):
    """Build the compatibility graph for max-clique. Nodes as defined;
    edge iff:
      - different cell, different piece.
      - if adjacent cells: facing edges match.
    """
    n = len(nodes)
    free_pos = {c: idx for idx, c in enumerate(free_cells)}
    g = ig.Graph(n=n, directed=False)
    edges = []

    # Group nodes by cell for efficient iteration.
    by_cell = {}
    for i, (c, p, r) in enumerate(nodes):
        by_cell.setdefault(c, []).append(i)

    for i in range(n):
        ci, pi, ri = nodes[i]
        xi, yi = ci % W, ci // W
        for j in range(i + 1, n):
            cj, pj, rj = nodes[j]
            if pi == pj:
                continue  # same piece
            if ci == cj:
                continue  # same cell
            xj, yj = cj % W, cj // W
            # Adjacency check.
            dx, dy = xj - xi, yj - yi
            adjacent = (abs(dx) + abs(dy) == 1)
            if adjacent:
                # Determine facing sides.
                if dx == 1:
                    si, sj = 1, 3
                elif dx == -1:
                    si, sj = 3, 1
                elif dy == 1:
                    si, sj = 2, 0
                else:  # dy == -1
                    si, sj = 0, 2
                if int(piece_rot[pi, ri, si]) != int(piece_rot[pj, rj, sj]):
                    continue  # incompatible adjacent placement
            edges.append((i, j))
    g.add_edges(edges)
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_json")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--region-x", type=int, default=4)
    ap.add_argument("--region-y", type=int, default=8)
    ap.add_argument("--region-k", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-clique-timeout", type=int, default=120,
                    help="seconds before giving up on max-clique search")
    args = ap.parse_args()

    pieces, hints = load_puzzle(args.puzzle)
    piece_rot = piece_rotations_tensor(pieces)
    board, source_j = load_board(args.board_json)

    free_cells = region_cells(args.region_x, args.region_y, args.region_k)
    free_set = set(free_cells)
    # Pieces pinned OUTSIDE the region (not removable).
    pinned_pieces = set()
    for pos in range(N_CELLS):
        if pos in free_set:
            continue
        if board[pos] >= 0:
            pid, _ = unpack(board[pos])
            pinned_pieces.add(int(pid))

    initial_score = sum(
        1 for y in range(H) for x in range(W)
        if x + 1 < W and board[y*W+x] >= 0 and board[y*W+x+1] >= 0
        and int(piece_rot[*unpack(int(board[y*W+x])), 1]) ==
            int(piece_rot[*unpack(int(board[y*W+x+1])), 3])
        and int(piece_rot[*unpack(int(board[y*W+x])), 1]) != BORDER
    ) + sum(
        1 for y in range(H) for x in range(W)
        if y + 1 < H and board[y*W+x] >= 0 and board[(y+1)*W+x] >= 0
        and int(piece_rot[*unpack(int(board[y*W+x])), 2]) ==
            int(piece_rot[*unpack(int(board[(y+1)*W+x])), 0])
        and int(piece_rot[*unpack(int(board[y*W+x])), 2]) != BORDER
    )
    print(f"# initial total score: {initial_score}/480", file=sys.stderr)

    t0 = time.time()
    nodes, available = candidate_nodes(board, piece_rot, free_cells,
                                        pieces.shape[0], pinned_pieces)
    print(f"# {len(nodes)} candidate placement nodes (avg {len(nodes)/len(free_cells):.1f} per cell)",
          file=sys.stderr)
    print(f"# graph construction: {time.time()-t0:.2f}s", file=sys.stderr)

    t1 = time.time()
    g = build_compatibility_graph(nodes, free_cells, piece_rot)
    print(f"# graph: {g.vcount()} nodes, {g.ecount()} edges "
          f"(density {2*g.ecount()/(g.vcount()*(g.vcount()-1)):.3f})",
          file=sys.stderr)
    print(f"# graph build: {time.time()-t1:.2f}s", file=sys.stderr)

    if g.vcount() == 0:
        print("ERROR: no candidate nodes (boundary too restrictive)", file=sys.stderr)
        sys.exit(2)

    t2 = time.time()
    target = len(free_cells)
    # Try to find a clique of size = target (= full region fill).
    # python-igraph has `largest_cliques()` (returns ALL max cliques)
    # and `clique_number()` (just the size).
    print(f"# searching for clique of size {target}...", file=sys.stderr)
    largest = g.largest_cliques()
    print(f"# max clique size: {len(largest[0]) if largest else 0}", file=sys.stderr)
    print(f"# {len(largest)} max-cliques found, max-clique search: {time.time()-t2:.2f}s",
          file=sys.stderr)

    if not largest or len(largest[0]) < target:
        print(f"# no perfect region fill found (largest={len(largest[0]) if largest else 0}, target={target})",
              file=sys.stderr)
        # Report largest found.
        clique = largest[0] if largest else []
        # Show what it would look like.
        placement_in_region = {}
        for node_idx in clique:
            c, p, r = nodes[node_idx]
            placement_in_region[c] = (p, r)
        print(f"# partial fill ({len(placement_in_region)}/{target} cells):",
              file=sys.stderr)
        for c in sorted(placement_in_region.keys()):
            p, r = placement_in_region[c]
            print(f"#   cell ({c%W},{c//W}): piece={p} rot={r}", file=sys.stderr)
        sys.exit(0)

    # Perfect fill found. Apply it.
    print(f"# *** PERFECT FILL FOUND for {args.region_k}x{args.region_k} region ***",
          file=sys.stderr)
    clique = largest[0]
    new_board = board.copy()
    for node_idx in clique:
        c, p, r = nodes[node_idx]
        new_board[c] = pack(p, r)
    # Compute new score.
    new_score = sum(
        1 for y in range(H) for x in range(W)
        if x + 1 < W and new_board[y*W+x] >= 0 and new_board[y*W+x+1] >= 0
        and int(piece_rot[*unpack(int(new_board[y*W+x])), 1]) ==
            int(piece_rot[*unpack(int(new_board[y*W+x+1])), 3])
        and int(piece_rot[*unpack(int(new_board[y*W+x])), 1]) != BORDER
    ) + sum(
        1 for y in range(H) for x in range(W)
        if y + 1 < H and new_board[y*W+x] >= 0 and new_board[(y+1)*W+x] >= 0
        and int(piece_rot[*unpack(int(new_board[y*W+x])), 2]) ==
            int(piece_rot[*unpack(int(new_board[(y+1)*W+x])), 0])
        and int(piece_rot[*unpack(int(new_board[y*W+x])), 2]) != BORDER
    )
    print(f"# new total score: {new_score}/480 (delta {new_score - initial_score:+d})",
          file=sys.stderr)


if __name__ == "__main__":
    main()
