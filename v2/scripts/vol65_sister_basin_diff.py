#!/usr/bin/env python3
"""Vol-65 — Detailed diff of sister 458 basins from vol-61 stage 3.

The two boards (seed17 + seed200) have:
- Same score: 458/480
- Same pipeline: vanilla_path border-first 30min -> ALNS minimal 5min
                 -> ALNS basic 30min from same stage-2 partial (453)
- Only differ in 46 cells (out of 256)

Goal: characterize the differing-cells geometry. Are they in the
defect regions of each board? Are they a connected sub-region?
Are they pieces involved in cycle-swaps (sigma-cycle decomposition)?
"""

import collections
import json
import urllib.parse
from pathlib import Path


def load_placement(path):
    with open(path) as f:
        d = json.load(f)
    arr = d.get("placement", [])
    pos_to_piece = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = item.get("pos", idx)
        pid = item["piece_id"]
        rot = item["rotation"]
        pos_to_piece[pos] = (pid, rot)
    return pos_to_piece, d


def load_grid_from_bucas(d):
    url = d.get("bucas_url", "")
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).fragment)
    if "board_edges" not in qs:
        return None
    s = qs["board_edges"][0]
    if len(s) != 1024:
        return None
    g = [[None] * 16 for _ in range(16)]
    for i in range(256):
        r, c = divmod(i, 16)
        seg = s[i * 4 : (i + 1) * 4]
        g[r][c] = (seg[0], seg[1], seg[2], seg[3])
    return g


def defect_cells(g):
    """Return set of (r, c) cells incident on a mismatch."""
    if g is None:
        return set()
    out = set()
    for r in range(16):
        for c in range(15):
            if g[r][c][1] != g[r][c + 1][3]:
                out.add((r, c)); out.add((r, c + 1))
    for r in range(15):
        for c in range(16):
            if g[r][c][2] != g[r + 1][c][0]:
                out.add((r, c)); out.add((r + 1, c))
    return out


def main():
    paths = [
        ("seed17", "output/vol-61/faithful_sota_20260515T174124/stage3_seed17.json"),
        ("seed200", "output/vol-61/faithful_sota_20260515T174124/stage3_seed200.json"),
    ]
    boards = {}
    grids = {}
    for name, p in paths:
        pl, d = load_placement(p)
        boards[name] = pl
        grids[name] = load_grid_from_bucas(d)
        defects = defect_cells(grids[name])
        print(f"{name}: {len(pl)} pieces, {len(defects)} defect cells")

    # Find cells where placement differs
    diff_cells = []
    pos_sets = sorted(set(boards["seed17"].keys()) | set(boards["seed200"].keys()))
    for pos in pos_sets:
        a = boards["seed17"].get(pos)
        b = boards["seed200"].get(pos)
        if a != b:
            diff_cells.append(pos)
    print(f"\nDiffering cells: {len(diff_cells)}")

    # Diff cells geometry: positions (x, y)
    diff_xy = [(pos % 16, pos // 16) for pos in diff_cells]
    xs = [x for x, y in diff_xy]
    ys = [y for x, y in diff_xy]
    print(f"Diff cells bounding box: x[{min(xs)}..{max(xs)}], y[{min(ys)}..{max(ys)}]")
    print(f"Diff cells (sorted):")
    sorted_diff = sorted(diff_xy, key=lambda t: (t[1], t[0]))
    for i in range(0, len(sorted_diff), 8):
        row = sorted_diff[i : i + 8]
        print(f"  {row}")

    # Connectedness: 4-neighbour subgraph on diff_cells
    diff_set = set(diff_xy)
    visited = set()
    comps = []
    for cell in diff_set:
        if cell in visited:
            continue
        comp = []
        stack = [cell]
        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue
            visited.add((x, y))
            comp.append((x, y))
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) in diff_set and (nx, ny) not in visited:
                    stack.append((nx, ny))
        comps.append(comp)
    print(f"\nDiff-cells form {len(comps)} 4-connected components:")
    for c in sorted(comps, key=len, reverse=True):
        xs = [x for x, _ in c]; ys = [y for _, y in c]
        print(f"  size={len(c)} bbox=x[{min(xs)}..{max(xs)}] y[{min(ys)}..{max(ys)}]")

    # Sigma cycle: piece-id permutation. For each cell where piece differs,
    # what piece is THERE in seed17 vs seed200?
    # Build piece->position maps
    p17 = {pid: pos for pos, (pid, _) in boards["seed17"].items()}
    p200 = {pid: pos for pos, (pid, _) in boards["seed200"].items()}

    # sigma: piece-permutation. sigma(p) = where p went in seed200 if p is at
    # different position than seed17.
    moved_pieces = []
    for pid in p17:
        if p17[pid] != p200.get(pid):
            moved_pieces.append(pid)
    print(f"\nPieces moved between basins: {len(moved_pieces)}")
    print(f"Cycle decomposition of sigma = (pos_in_s17 -> pos_in_s200):")
    # Sigma at the POSITION level: for each pos, what piece occupies it in s17 vs s200
    sigma = {}
    for pos in diff_cells:
        pid_s17 = boards["seed17"][pos][0]
        # where is pid_s17 in seed200?
        pos_in_s200 = p200.get(pid_s17)
        if pos_in_s200 is not None and pos_in_s200 != pos:
            sigma[pos] = pos_in_s200
    # Trace cycles
    visited = set()
    cycles = []
    for start in sigma:
        if start in visited:
            continue
        cycle = []
        cur = start
        while cur not in visited and cur in sigma:
            visited.add(cur)
            cycle.append(cur)
            cur = sigma[cur]
        if len(cycle) >= 2:
            cycles.append(cycle)
    print(f"Number of nontrivial cycles: {len(cycles)}")
    for c in sorted(cycles, key=len, reverse=True):
        print(f"  cycle of length {len(c)}: pos {c[:6]}{'...' if len(c) > 6 else ''}")

    # Overlap with defect cells
    d17 = defect_cells(grids["seed17"])
    d200 = defect_cells(grids["seed200"])
    diff_xy_set = set(diff_xy)
    in_d17 = sum(1 for c in diff_xy if c in d17)
    in_d200 = sum(1 for c in diff_xy if c in d200)
    in_either = sum(1 for c in diff_xy if c in d17 or c in d200)
    in_both = sum(1 for c in diff_xy if c in d17 and c in d200)
    print(f"\nDefect-cell overlap:")
    print(f"  diff cells: {len(diff_xy)}")
    print(f"  ∩ defect(s17): {in_d17} / {len(d17)}")
    print(f"  ∩ defect(s200): {in_d200} / {len(d200)}")
    print(f"  ∩ either defect set: {in_either}")
    print(f"  ∩ BOTH defect sets: {in_both}")


if __name__ == "__main__":
    main()
