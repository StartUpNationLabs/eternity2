#!/usr/bin/env python3
"""Cell-defect MWPM destroy-set generator for E2 plateau boards.

Implements the A2-vol-4 recommendation: model each plateau board's
defective cells (cells incident to >= 1 mismatched edge) as nodes,
build a complete graph weighted by pairwise distance/feasibility,
and run min-weight perfect matching (PyMatching v2) to pair them up.
The matched-pair set defines a destroy region for ALNS: each pair's
two cells (plus the L1 path between them) is destroyed and re-solved.

The hypothesis (per Higgott-Gidney 2025 Sparse Blossom for surface
codes): pairing defects by spatial proximity gives the LOWEST-COST
joint repair, in the surface-code analog. For E2 the analog is
imperfect because piece-uniqueness constraints couple distant cells,
but the spatial proximity heuristic is a sensible starting weight.

Future weight extensions:
- Bipartite-feasibility weight: w(a, b) = -log p(both cells can be
  re-piece-swapped without breaking the surrounding rim). Computed by
  a bounded CP probe.
- Hamming-distance-along-path: count of intermediate cells that would
  also need to change.

Usage:
    python3 scripts/cell_defect_mwpm.py BOARD_JSON [--max-pairs N]
    Reads board from bucas_url field. Emits a JSON with:
      {"defect_cells": [[x,y],...],
       "pairs": [[(x1,y1),(x2,y2)],...],
       "destroy_set": [pos1, pos2, ...]}

EXPERIMENTAL: differs from `MwpmDefectPair` in alns.rs which operates
on edge midpoints; this operates on CELLS as the surface-code-style
literature recommends.
"""

import argparse
import json
import re
import sys

import numpy as np

try:
    import pymatching
except ImportError as e:
    print(f"pip install pymatching: {e}", file=sys.stderr)
    sys.exit(2)

W = 16
H = 16
BORDER = 0


def parse_bucas(url):
    m = re.search(r'board_edges=([a-z]+)', url)
    if not m:
        return None
    blob = m.group(1)
    return [
        tuple(ord(blob[pos * 4 + i]) - ord('a') for i in range(4))
        for pos in range(W * H)
    ]


def find_defect_cells(quads):
    """Cells incident to at least one mismatched interior edge."""
    incident = set()
    for y in range(H):
        for x in range(W):
            pos = y * W + x
            if x + 1 < W:
                a, b = quads[pos][1], quads[pos + 1][3]
                if a != BORDER and b != BORDER and a != b:
                    incident.add(pos)
                    incident.add(pos + 1)
            if y + 1 < H:
                a, b = quads[pos][2], quads[pos + W][0]
                if a != BORDER and b != BORDER and a != b:
                    incident.add(pos)
                    incident.add(pos + W)
    return sorted(incident)


def manhattan(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def build_matching(defect_positions, use_boundary_for_odd=False):
    """Build a PyMatching v2 Matching object on the complete graph
    over defect_positions, with edges weighted by Manhattan distance.

    PyMatching v2's `decode_to_matched_dets_array(syndrome)` pairs up
    syndrome=1 detectors via min-weight matching on the matching graph.
    Real-real edges only; PyMatching will return -1 partners only if
    the graph has explicit boundary edges.

    For E2 plateau boards the defect count is typically odd. Options:
    - DROP the lowest-priority defect (highest Manhattan distance to
      its nearest neighbour, = most isolated).
    - Add expensive boundary edges (cost = MAX_MANHATTAN) so all
      real-real pairings dominate; one defect ends up matched to
      boundary = "ignored" by the destroy set.
    """
    n = len(defect_positions)
    coords = [(p % W, p // W) for p in defect_positions]
    matching = pymatching.Matching()
    for i in range(n):
        for j in range(i + 1, n):
            w = manhattan(coords[i], coords[j])
            matching.add_edge(i, j, weight=float(max(w, 1)),
                              fault_ids={i, j})
    if n % 2 == 1 and use_boundary_for_odd:
        # Boundary edge weight = 2 * W (= diagonal of the board);
        # forces the matching to prefer real-real pairings whenever
        # possible.
        bdry_w = float(2 * W)
        for i in range(n):
            matching.add_boundary_edge(i, weight=bdry_w, fault_ids={i})
    return matching, coords


def decode_matching(matching, defect_positions, coords):
    """Run min-weight perfect matching by setting all defects as
    syndromes and ask PyMatching for the fault pattern."""
    n = len(defect_positions)
    # Syndrome: every defect node is "lit" → PyMatching pairs them up.
    # But PyMatching's syndrome is over EDGES (X-stabilizers), not
    # vertices, so the API is different. For a vertex-based MWPM we
    # use the approach: pretend each vertex is a syndrome bit, build
    # a separate "matching graph" where edges are the candidate pairs.
    #
    # Simpler workflow with PyMatching v2: use `decode` after
    # constructing a graph that represents the desired matching.
    syndrome = np.ones(n, dtype=np.uint8)
    try:
        prediction = matching.decode(syndrome)
    except Exception as e:
        print(f"PyMatching decode error (n={n}): {e}", file=sys.stderr)
        return [], 0
    # prediction is a 1D array of fault_ids that fired; since we set
    # fault_ids={i, j} on each pair-edge, a fired prediction[i]=1
    # indicates that real-defect i is part of a chosen edge.
    # PyMatching MWPM returns: the set of edges chosen to flip given
    # syndromes; we can iterate matching.edges() to find which pairs
    # had non-zero contribution, but easier: rerun the algorithm with
    # explicit matching.decode_to_edges_array.
    return prediction, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_json")
    ap.add_argument("--max-defects", type=int, default=80,
                    help="If defect count exceeds this, fail fast.")
    args = ap.parse_args()

    j = json.load(open(args.board_json))
    url = j.get("bucas_url", "")
    if not url:
        print("ERROR: no bucas_url in JSON", file=sys.stderr)
        sys.exit(1)
    quads = parse_bucas(url)
    if quads is None:
        print("ERROR: bucas parse failed", file=sys.stderr)
        sys.exit(1)

    defects = find_defect_cells(quads)
    print(f"# defect cells (incident to ≥1 mismatched edge): {len(defects)}",
          file=sys.stderr)
    if not defects:
        print(json.dumps({"defect_cells": [], "pairs": [], "destroy_set": []}))
        return
    if len(defects) > args.max_defects:
        print(f"ERROR: too many defects ({len(defects)} > {args.max_defects})",
              file=sys.stderr)
        sys.exit(2)

    odd_handling = (len(defects) % 2 == 1)
    matching, coords = build_matching(defects, use_boundary_for_odd=odd_handling)
    print(f"# graph built: {len(defects)} defects (odd={odd_handling})",
          file=sys.stderr)

    # PyMatching API: `decode_to_matched_dets_array(syndrome)` returns
    # an array of shape (n_pairs, 2) with the indices of matched
    # detector pairs.
    syndrome = np.ones(len(defects), dtype=np.uint8)
    try:
        matched_pairs = matching.decode_to_matched_dets_array(syndrome)
    except Exception as e:
        print(f"decode error: {e}", file=sys.stderr)
        print(json.dumps({"defect_cells": coords, "pairs": [], "destroy_set": []}))
        return

    pairs = []
    destroy_set = set()
    total_cost = 0
    for row in matched_pairs:
        i, jj = int(row[0]), int(row[1])
        # PyMatching uses -1 to denote boundary node.
        if i == -1 or jj == -1:
            if i != -1:
                destroy_set.add(defects[i])
                pairs.append((coords[i], "boundary"))
            if jj != -1:
                destroy_set.add(defects[jj])
                pairs.append((coords[jj], "boundary"))
            continue
        pa, pb = coords[i], coords[jj]
        destroy_set.add(defects[i])
        destroy_set.add(defects[jj])
        # Also add the Manhattan path between them.
        x1, y1 = pa; x2, y2 = pb
        sx = 1 if x2 >= x1 else -1
        sy = 1 if y2 >= y1 else -1
        for xx in range(x1, x2 + sx, sx):
            destroy_set.add(y1 * W + xx)
        for yy in range(y1, y2 + sy, sy):
            destroy_set.add(yy * W + x2)
        pairs.append((pa, pb))
        total_cost += manhattan(pa, pb)

    print(f"# matched pairs: {len(pairs)}, total Manhattan cost: {total_cost}",
          file=sys.stderr)
    print(f"# destroy set size: {len(destroy_set)} cells",
          file=sys.stderr)

    out = {
        "defect_cells": [{"x": c[0], "y": c[1]} for c in coords],
        "pairs": [
            {"a": list(p[0]) if isinstance(p[0], tuple) else p[0],
             "b": list(p[1]) if isinstance(p[1], tuple) else p[1]}
            for p in pairs
        ],
        "destroy_set": sorted(destroy_set),
        "total_cost": total_cost,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
