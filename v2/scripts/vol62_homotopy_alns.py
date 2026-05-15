#!/usr/bin/env python3
"""Vol-62 — Homotopy-ALNS prototype: β₁-cycle generators on E2 defect graphs.

Per `vault/concepts/homotopy-alns.md`. This script:

  1. Loads a board JSON (bucas_url field).
  2. Builds the defect graph (cells with ≥1 mismatched edge as nodes;
     mismatched edges as graph edges).
  3. Computes β₀, β₁ via the cyclomatic formula β₁ = E - V + β₀.
  4. Picks a spanning forest (DFS), enumerates β₁ generator cycles
     (non-tree edge + tree path between its endpoints).
  5. For each cycle, computes its planar interior (smaller face).
  6. Sorts by interior size, emits destroy-set candidates.

Output (JSON to stdout):

  {
    "score": int,                  # matched edges, 480 - |defect edges|
    "score_check": int,            # 480 - len(edges)
    "V": int, "E": int, "C": int,  # defect graph
    "beta_1": int,
    "cycles": [
      {
        "cycle_id": int,
        "length_edges": int,
        "length_cells": int,
        "interior_size": int,
        "destroy_positions": [int, ...]   # board positions (row*16+col)
      },
      ...
    ]
  }

Usage:
  vol62_homotopy_alns.py BOARD_JSON [--top N] [--emit-cycles PATH]
"""

import argparse
import collections
import json
import sys
import urllib.parse


def parse_board_from_json(path):
    """Return a 16x16 grid where grid[r][c] = (T,R,B,L) color chars."""
    with open(path) as f:
        data = json.load(f)
    board_str = None
    if "bucas_url" in data:
        url = data["bucas_url"]
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.fragment)
        if "board_edges" in qs:
            board_str = qs["board_edges"][0]
    if board_str is None:
        sys.exit("no bucas_url/board_edges in JSON")
    assert len(board_str) == 1024, f"board_str length {len(board_str)} != 1024"
    grid = [[None] * 16 for _ in range(16)]
    for i in range(256):
        r, c = divmod(i, 16)
        s = board_str[i * 4 : (i + 1) * 4]
        grid[r][c] = (s[0], s[1], s[2], s[3])
    return grid, data.get("matched")


def defect_edges(grid):
    """Return list of (u, v) edges where u, v are cells (r,c) of mismatches.

    Edge orientation is canonical: u < v (lex order).
    """
    edges = []
    # horizontal: R(c) vs L(c+1)
    for r in range(16):
        for c in range(15):
            if grid[r][c][1] != grid[r][c + 1][3]:
                u, v = (r, c), (r, c + 1)
                edges.append((u, v))
    # vertical: B(r) vs T(r+1)
    for r in range(15):
        for c in range(16):
            if grid[r][c][2] != grid[r + 1][c][0]:
                u, v = (r, c), (r + 1, c)
                edges.append((u, v))
    return edges


def defect_graph(edges):
    """Adjacency dict from edge list."""
    adj = collections.defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def connected_components(vertices, adj):
    """DFS-based connected components. Returns list of vertex sets."""
    seen = set()
    comps = []
    for s in vertices:
        if s in seen:
            continue
        comp = set()
        stack = [s]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            comp.add(v)
            stack.extend(adj[v] - seen)
        comps.append(comp)
    return comps


def spanning_forest_dfs(vertices, adj):
    """Return (tree_edges_set, parent dict)."""
    tree_edges = set()
    parent = {}
    seen = set()
    for s in vertices:
        if s in seen:
            continue
        parent[s] = None
        stack = [s]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            for w in adj[v]:
                if w not in seen:
                    parent[w] = v
                    e = (min(v, w), max(v, w))
                    tree_edges.add(e)
                    stack.append(w)
    return tree_edges, parent


def path_in_tree(u, v, parent):
    """Return list of vertices on the tree path from u to v (inclusive).

    Uses bfs since the tree is sparse and small. For β₁-many cycles, the
    cost is O(β₁ · diameter), acceptable here (β₁ < 50 typical).
    """
    # ancestor sets via parent chain
    def ancestors(x):
        chain = [x]
        while parent.get(x) is not None:
            x = parent[x]
            chain.append(x)
        return chain

    au = ancestors(u)
    av = ancestors(v)
    set_av = {x: i for i, x in enumerate(av)}
    for i, x in enumerate(au):
        if x in set_av:
            j = set_av[x]
            return au[: i + 1] + av[:j][::-1]
    raise RuntimeError(f"no path from {u} to {v} — different components?")


def cycle_cells(cycle_verts):
    """Cells touched by the cycle (just the vertices on the loop)."""
    return list(cycle_verts)


def cycle_interior(cycle_verts):
    """Compute the smaller planar face bounded by the cycle.

    Uses bounding box of the cycle + flood fill from outside. Cells in
    the bbox not reachable from outside-of-bbox are interior.

    This is APPROXIMATE: it works when the cycle is a simple closed loop
    in the grid. For self-touching cycles it may over-count.

    Returns set of (r, c) cells STRICTLY INSIDE (cycle vertices excluded).
    """
    if not cycle_verts:
        return set()
    rs = [r for r, _ in cycle_verts]
    cs = [c for _, c in cycle_verts]
    rmin, rmax = min(rs), max(rs)
    cmin, cmax = min(cs), max(cs)

    cycle_set = set(cycle_verts)
    # Pad bbox by 1 on each side so we have a guaranteed "outside" ring.
    rlo, rhi = max(0, rmin - 1), min(15, rmax + 1)
    clo, chi = max(0, cmin - 1), min(15, cmax + 1)

    # Flood-fill from any boundary cell of the padded bbox that's NOT in
    # cycle_set.
    outside = set()
    queue = collections.deque()
    for r in range(rlo, rhi + 1):
        for c in (clo, chi):
            v = (r, c)
            if v not in cycle_set:
                outside.add(v)
                queue.append(v)
    for c in range(clo, chi + 1):
        for r in (rlo, rhi):
            v = (r, c)
            if v not in cycle_set and v not in outside:
                outside.add(v)
                queue.append(v)

    while queue:
        r, c = queue.popleft()
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if rlo <= nr <= rhi and clo <= nc <= chi:
                v = (nr, nc)
                if v not in cycle_set and v not in outside:
                    outside.add(v)
                    queue.append(v)

    # Interior = bbox cells not in cycle and not reached
    interior = set()
    for r in range(rlo, rhi + 1):
        for c in range(clo, chi + 1):
            v = (r, c)
            if v not in cycle_set and v not in outside:
                interior.add(v)
    return interior


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_json")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--emit-cycles", default=None)
    args = ap.parse_args()

    grid, matched_claim = parse_board_from_json(args.board_json)
    edges = defect_edges(grid)
    V_set = set()
    for u, v in edges:
        V_set.add(u)
        V_set.add(v)
    adj = defect_graph(edges)
    comps = connected_components(V_set, adj)
    V = len(V_set)
    E = len(edges)
    C = len(comps)
    beta_1 = E - V + C
    score = 480 - E

    tree_edges, parent = spanning_forest_dfs(V_set, adj)
    non_tree = [
        (u, v) for (u, v) in edges if (min(u, v), max(u, v)) not in tree_edges
    ]
    assert len(non_tree) == beta_1, (
        f"non_tree count {len(non_tree)} != beta_1 {beta_1}"
    )

    cycles = []
    for idx, (u, v) in enumerate(non_tree):
        path_uv = path_in_tree(u, v, parent)
        interior = cycle_interior(path_uv)
        destroy_cells = set(path_uv) | interior
        positions = sorted(r * 16 + c for (r, c) in destroy_cells)
        cycles.append(
            {
                "cycle_id": idx,
                "length_cells": len(path_uv),
                "interior_size": len(interior),
                "destroy_size": len(destroy_cells),
                "cycle_cells_rc": [list(rc) for rc in path_uv],
                "interior_cells_rc": [list(rc) for rc in sorted(interior)],
                "destroy_positions": positions,
            }
        )

    cycles.sort(key=lambda c: (c["destroy_size"], c["length_cells"]))

    out = {
        "board_json": args.board_json,
        "score": score,
        "matched_claim": matched_claim,
        "V": V,
        "E": E,
        "C": C,
        "beta_1": beta_1,
        "n_components": C,
        "tree_edges": len(tree_edges),
        "non_tree_edges": len(non_tree),
        "cycles": cycles[: args.top],
    }
    print(json.dumps(out, indent=2))

    if args.emit_cycles:
        with open(args.emit_cycles, "w") as f:
            json.dump(out, f, indent=2)
        print(f"# wrote {args.emit_cycles}", file=sys.stderr)


if __name__ == "__main__":
    main()
