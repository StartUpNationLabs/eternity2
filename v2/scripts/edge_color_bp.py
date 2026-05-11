#!/usr/bin/env python3
"""Minimal loopy belief propagation on the edge-color factor graph of E2.

EXPERIMENTAL — overnight probe against research-agent's structural
prediction that the cavity assumption breaks on a short-cycle factor
graph. We are NOT trying to solve E2 via BP; we are asking:

  - Does BP CONVERGE on this graph, or oscillate/explode (consistent
    with cavity-method failure)?
  - If it converges, are the resulting edge-color marginals confident
    on edges we know to be matched (from the 450 board)? If yes, BP
    might be useful as a frozen-mass oracle to seed CP/PT.
  - Specifically: how does BP score the 6 universal-mismatch edges?
    Low-confidence marginals there would empirically validate the
    "structurally-hard" hypothesis.

MODEL: cell-compatibility-only relaxation.
  - Variables: x_e ∈ {0, 1..22} for each interior edge. BORDER edges
    are clamped to 0.
  - Factors: one per cell. Factor_c(x_top, x_right, x_bottom, x_left) = 1
    iff (top, right, bottom, left) ∈ ⋃_p rotations_of(p) over the 256 pieces.
  - Hints: clamp the 4 edges of each hint cell.
  - WE IGNORE the all-different constraint over pieces (= a global
    constraint of arity 256). This is a relaxation; expect spurious
    solutions if BP converges.

Output: per-edge marginal as a (22+1)-dim vector. Entropy per edge.
Top-6 universal mismatch edges flagged.
"""

import argparse
import csv
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

W = 16
H = 16
N_CELLS = W * H
N_COLORS = 22  # interior colors 1..22; BORDER = 0
DOMAIN = N_COLORS + 1  # 0..22


def parse_csv_piece_word(s):
    v = int(s.strip(), 2)
    if v == 65535:
        return 0  # BORDER
    return v


def load_puzzle(path):
    """Returns (pieces, hints).
    pieces: list of (top, right, bottom, left), 256 entries.
    hints: dict pos -> (piece_id, rotation).
    """
    pieces = []
    hints = {}
    with open(path) as f:
        first = f.readline().strip()
        size = int(first)
        assert size == W
        for pid, line in enumerate(f):
            cols = line.strip().split(',')
            if len(cols) < 4:
                continue
            top = parse_csv_piece_word(cols[0])
            right = parse_csv_piece_word(cols[1])
            bottom = parse_csv_piece_word(cols[2])
            left = parse_csv_piece_word(cols[3])
            pieces.append((top, right, bottom, left))
            if len(cols) >= 7:
                x = int(cols[4])
                y = int(cols[5])
                rot = int(cols[6])
                if (x, y, rot) != (0, 0, 0):
                    pos = y * W + x
                    hints[pos] = (pid, rot)
    return pieces, hints


def rotate_quad(q, rot):
    """q = (top, right, bottom, left). Rotation rot ∈ {0,1,2,3} = 0,90,180,270 CW."""
    top, right, bottom, left = q
    if rot == 0:
        return top, right, bottom, left
    if rot == 1:
        return left, top, right, bottom
    if rot == 2:
        return bottom, left, top, right
    if rot == 3:
        return right, bottom, left, top
    raise ValueError(rot)


def build_cell_factor_tables(pieces):
    """For each cell class (corner/edge/interior), build a SET of
    valid (top, right, bottom, left) quads over all pieces × all 4
    rotations. The factor for a cell is the indicator over this set.

    For BP we don't actually need to enumerate; we just check
    membership at message-update time. We materialize the full set as
    a dict (top, right, bottom, left) -> 1 for O(1) lookup.

    Returns: a single set of valid quads across ALL pieces × rotations.
    We don't restrict by cell-class — BP is a relaxation.
    """
    valid = set()
    for q in pieces:
        for rot in range(4):
            valid.add(rotate_quad(q, rot))
    return valid


# ----- edge indexing -----
# For each cell (x,y), its 4 edges are:
#   side 0 (top):    horizontal edge at row y, between (x, y-1) and (x, y).
#                    If y=0, top is BORDER (clamped).
#   side 1 (right):  vertical edge at col x+1.
#   side 2 (bottom): horizontal edge at row y+1.
#   side 3 (left):   vertical edge at col x.
#
# We give each edge an integer index. Horizontal edges: indexed by
# (row, col) where row ∈ [0..H], col ∈ [0..W). Vertical: (row, col)
# where row ∈ [0..H), col ∈ [0..W].

def edge_id(orient, row, col):
    """orient: 'h' or 'v'. Returns a global edge index, or -1 if invalid."""
    if orient == 'h':
        if row < 0 or row > H or col < 0 or col >= W:
            return -1
        return row * W + col
    if orient == 'v':
        if row < 0 or row >= H or col < 0 or col > W:
            return -1
        return (H + 1) * W + row * (W + 1) + col
    raise ValueError(orient)


N_EDGES = (H + 1) * W + H * (W + 1)


def cell_edges(x, y):
    """4 edges (top, right, bottom, left), each as global edge index."""
    top = edge_id('h', y, x)
    right = edge_id('v', y, x + 1)
    bottom = edge_id('h', y + 1, x)
    left = edge_id('v', y, x)
    return top, right, bottom, left


def is_border_edge(eid):
    """An edge is BORDER iff its row/col on the boundary of the board."""
    if eid < (H + 1) * W:
        # horizontal: row in [0..H], col in [0..W)
        row = eid // W
        return row == 0 or row == H
    eid2 = eid - (H + 1) * W
    col = eid2 % (W + 1)
    return col == 0 or col == W


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--max-iters", type=int, default=200)
    ap.add_argument("--damping", type=float, default=0.5)
    ap.add_argument("--conv-tol", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    pieces, hints = load_puzzle(args.puzzle)
    print(f"loaded {len(pieces)} pieces, {len(hints)} hints", file=sys.stderr)

    # Build the cell-compatibility set.
    t0 = time.time()
    valid_quads = build_cell_factor_tables(pieces)
    print(f"valid quad set size: {len(valid_quads)} (out of {DOMAIN**4} possible)", file=sys.stderr)
    print(f"  factor build: {time.time()-t0:.2f}s", file=sys.stderr)

    # For each cell, precompute the set of valid quads.
    # All cells share the same valid set (we don't restrict by cell-class).

    # Edges: assign clamped values for borders + hint-incident edges.
    # clamp[e] = None means free; otherwise an int color.
    clamp = [None] * N_EDGES
    for eid in range(N_EDGES):
        if is_border_edge(eid):
            clamp[eid] = 0  # BORDER

    # Apply hints: pin all 4 edges of each hinted cell.
    for pos, (pid, rot) in hints.items():
        y, x = pos // W, pos % W
        q = rotate_quad(pieces[pid], rot)
        for side, eid in enumerate(cell_edges(x, y)):
            if eid < 0:
                continue
            clamp[eid] = q[side]

    n_clamped = sum(1 for c in clamp if c is not None)
    print(f"clamped edges: {n_clamped}/{N_EDGES} (border + hints)", file=sys.stderr)

    # ----- BP messages -----
    # Each edge has a (DOMAIN,)-vector message to each incident cell.
    # An interior edge is incident to 2 cells (left/right or top/bottom);
    # border edges are incident to 1 cell (clamped).
    #
    # m_{e→c}(color) ∝ ∏_{c' ≠ c, c' ∋ e} sum_{x_{partners} ~ valid_at_c'} ...
    #
    # We use the standard factor-graph BP: edge-variable nodes, cell-factor
    # nodes. Messages flow:
    #   factor → variable: at cell c, message to edge e = sum over the
    #     other 3 edges' values of [factor_c(quad) * ∏ other_var→c msgs]
    #   variable → factor: at edge e, message to cell c = ∏ msgs from
    #     OTHER factors incident to e
    #
    # Damped iteration. Initial: uniform messages.
    rng = np.random.RandomState(args.seed)

    # cell_to_edges[c] = (top_eid, right_eid, bottom_eid, left_eid) per cell c
    cell_to_edges = [cell_edges(c % W, c // W) for c in range(N_CELLS)]
    edge_to_cells = [[] for _ in range(N_EDGES)]
    for c, edges in enumerate(cell_to_edges):
        for side, e in enumerate(edges):
            if e < 0:
                continue
            edge_to_cells[e].append((c, side))

    # Message storage:
    # m_cell_to_edge[c, side, color] = msg from cell c (factor) → edge on side
    # m_edge_to_cell[c, side, color] = msg from edge → cell c on its side
    m_c2e = np.ones((N_CELLS, 4, DOMAIN), dtype=np.float64) / DOMAIN
    m_e2c = np.ones((N_CELLS, 4, DOMAIN), dtype=np.float64) / DOMAIN

    # Convert valid_quads to a numpy array of shape (V, 4) for fast iteration.
    valid_arr = np.array(list(valid_quads), dtype=np.int32)
    print(f"valid_arr: {valid_arr.shape}", file=sys.stderr)
    print(f"running BP: max_iters={args.max_iters} damping={args.damping}", file=sys.stderr)

    # Iteration.
    for it in range(args.max_iters):
        t_it = time.time()

        # ----- factor → variable updates -----
        # For each cell, for each side, compute msg to edge[side]:
        #   m_c2e[c, side, color] = Σ_{quads where quads[side]=color} ∏_{s'≠side} m_e2c[c, s', quads[s']]
        new_m_c2e = np.zeros_like(m_c2e)
        for c in range(N_CELLS):
            # Get the 4 incoming msgs (edge→cell on each side).
            incoming = m_e2c[c]  # shape (4, DOMAIN)
            # For each valid quad, compute the product of incoming msgs
            # at the 4 sides, then accumulate.
            # quads[v] = (top, right, bottom, left) values in DOMAIN.
            #
            # Honor clamps: incoming msg from a clamped edge is a
            # one-hot already (because the edge's marginal is fixed),
            # which is enforced when we update m_e2c. Here we just use
            # the current m_e2c.
            ps = incoming[0, valid_arr[:, 0]] * incoming[1, valid_arr[:, 1]] \
                * incoming[2, valid_arr[:, 2]] * incoming[3, valid_arr[:, 3]]
            # For msg to side `s`, exclude that side's incoming factor.
            for s in range(4):
                # Skip the incoming[s, value] factor.
                excl = ps / np.maximum(incoming[s, valid_arr[:, s]], 1e-30)
                np.add.at(new_m_c2e[c, s], valid_arr[:, s], excl)
            # normalize per-side.
            for s in range(4):
                z = new_m_c2e[c, s].sum()
                if z > 0:
                    new_m_c2e[c, s] /= z
                else:
                    new_m_c2e[c, s] = 1.0 / DOMAIN

        # Damp.
        m_c2e = args.damping * m_c2e + (1.0 - args.damping) * new_m_c2e
        # Re-normalize after damping
        for c in range(N_CELLS):
            for s in range(4):
                z = m_c2e[c, s].sum()
                if z > 0:
                    m_c2e[c, s] /= z

        # ----- variable → factor updates -----
        # For an edge e shared by 2 cells (a, b):
        #   m_e2c[a, side_a, color] = m_c2e[b, side_b, color] if free
        #                              = δ(color = clamp[e]) if clamped
        # i.e., the var→factor msg from an edge to one of its cells is
        # just the factor→var msg from the OTHER incident cell.
        new_m_e2c = np.zeros_like(m_e2c)
        for e in range(N_EDGES):
            incs = edge_to_cells[e]
            if clamp[e] is not None:
                # Force one-hot.
                for c, s in incs:
                    new_m_e2c[c, s, :] = 0.0
                    new_m_e2c[c, s, clamp[e]] = 1.0
            elif len(incs) == 2:
                (ca, sa), (cb, sb) = incs
                new_m_e2c[ca, sa] = m_c2e[cb, sb]
                new_m_e2c[cb, sb] = m_c2e[ca, sa]
            elif len(incs) == 1:
                # Edge on boundary of board with only one incident cell.
                # If free, uniform; we shouldn't hit this for board interiors.
                (ca, sa) = incs[0]
                new_m_e2c[ca, sa] = 1.0 / DOMAIN

        # Damp & store.
        delta = np.max(np.abs(new_m_e2c - m_e2c))
        m_e2c = args.damping * m_e2c + (1.0 - args.damping) * new_m_e2c

        print(f"  iter {it+1:3d}: max-delta={delta:.6f}  ({time.time()-t_it:.2f}s/iter)",
              file=sys.stderr)
        if delta < args.conv_tol:
            print(f"  CONVERGED at iter {it+1}", file=sys.stderr)
            break

    # ----- compute marginals -----
    # marg[e, color] ∝ ∏_{c ∋ e} m_c2e[c, side_c_for_e, color]
    marginals = np.ones((N_EDGES, DOMAIN), dtype=np.float64)
    for e in range(N_EDGES):
        if clamp[e] is not None:
            marginals[e, :] = 0.0
            marginals[e, clamp[e]] = 1.0
            continue
        for c, s in edge_to_cells[e]:
            marginals[e] *= m_c2e[c, s]
        z = marginals[e].sum()
        if z > 0:
            marginals[e] /= z
        else:
            marginals[e] = 1.0 / DOMAIN

    # Entropy per edge.
    eps = 1e-12
    entropy = -np.sum(marginals * np.log(marginals + eps), axis=1)
    max_h = math.log(DOMAIN)

    # Now report on the 6 universal-mismatch edges. Their indexing in
    # our cell-position format (h, pos) means: pos is a cell index,
    # 'h' means the horizontal edge between cell pos and cell pos+1
    # (= the right-edge of cell pos = the left-edge of cell pos+1).
    # In our edge_id scheme:
    #   ('h', pos): cell at (x, y) where x=pos%W, y=pos//W; this edge
    #     is the RIGHT edge of cell pos = vertical edge at (y, x+1).
    #     id = edge_id('v', y, x+1)
    #   ('v', pos): the BOTTOM edge of cell pos = horizontal edge at
    #     (y+1, x).
    #     id = edge_id('h', y+1, x)
    forbidden = [('h', 180), ('h', 91), ('v', 162), ('h', 188), ('v', 183), ('v', 180)]
    print("\n=== Top-6 universal-mismatch edges ===")
    print(f"{'edge':>10}  {'cell':>6}  {'clamped':>8}  {'max-prob':>9}  {'argmax':>7}  {'entropy/log(D)':>14}")
    for typ, pos in forbidden:
        x, y = pos % W, pos // W
        if typ == 'h':
            eid = edge_id('v', y, x + 1)
        else:
            eid = edge_id('h', y + 1, x)
        clamped = (clamp[eid] is not None)
        if clamped:
            print(f"  ('{typ}',{pos:3d})  ({x:2d},{y:2d})  clamped={clamped}  N/A")
        else:
            best_p = marginals[eid].max()
            best_c = int(marginals[eid].argmax())
            h_norm = entropy[eid] / max_h
            print(f"  ('{typ}',{pos:3d})  ({x:2d},{y:2d})  {clamped!s:>8}  {best_p:.4f}    {best_c:>7d}  {h_norm:.4f}")

    # Global summary.
    free_mask = np.array([c is None for c in clamp])
    n_free = free_mask.sum()
    free_entropy = entropy[free_mask] / max_h
    print(f"\nFree edges: {n_free}/{N_EDGES}")
    print(f"  normalized entropy  median: {np.median(free_entropy):.4f}")
    print(f"  normalized entropy  mean:   {np.mean(free_entropy):.4f}")
    print(f"  fraction of free edges with max_prob > 0.99 (frozen): "
          f"{(np.max(marginals[free_mask], axis=1) > 0.99).mean():.4f}")
    print(f"  fraction of free edges with max_prob > 0.5: "
          f"{(np.max(marginals[free_mask], axis=1) > 0.5).mean():.4f}")


if __name__ == "__main__":
    main()
