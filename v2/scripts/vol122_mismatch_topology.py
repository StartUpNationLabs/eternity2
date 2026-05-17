#!/usr/bin/env python3
"""Vol-122 K9 — Mismatch-graph topology analysis.

Cross-domain lens (refined from K8 FFT failure): instead of treating
the board as a color image, look at the MISMATCH MAP — a sparse binary
image of which edges fail to match. Apply topological measures:
- Connected component count.
- Total perimeter of mismatch clusters.
- Spatial autocorrelation.

Hypothesis: high-score boards have FEWER but LARGER mismatch clusters
(i.e., mismatches concentrate in 1-2 'bad regions'); medium-score
boards have many small scattered mismatches.

Usage:
  python3 scripts/vol122_mismatch_topology.py
"""
import json
import os
import sys

sys.path.insert(0, 'scripts')
try:
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
except ImportError as e:
    print("Could not import helpers:", e)
    sys.exit(1)


def board_to_mismatch_map(board_path, pieces):
    """Return two binary maps: horizontal (15x16) and vertical (16x15) mismatch."""
    with open(board_path) as f:
        data = json.load(f)
    m = {p['pos']: (p['piece_id'], p['rotation']) for p in data['placement']}
    placement = [[None] * SIDE for _ in range(SIDE)]
    for pos, (pid, rot) in m.items():
        if pid >= len(pieces): continue
        r, c = pos // SIDE, pos % SIDE
        placement[r][c] = rot_edges(pieces[pid], rot)

    h_mis = [[False] * SIDE for _ in range(SIDE - 1)]  # between row r and r+1
    v_mis = [[False] * (SIDE - 1) for _ in range(SIDE)]  # between col c and c+1

    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None:
                continue
            T, R, B, L = placement[r][c]
            # Right neighbor
            if c + 1 < SIDE and placement[r][c+1] is not None:
                nT, nR, nB, nL = placement[r][c+1]
                if R != nL or R == 0:
                    v_mis[r][c] = True
            # Bottom neighbor
            if r + 1 < SIDE and placement[r+1][c] is not None:
                nT, nR, nB, nL = placement[r+1][c]
                if B != nT or B == 0:
                    h_mis[r][c] = True
    return h_mis, v_mis


def count_mismatches(h_mis, v_mis):
    h_count = sum(sum(row) for row in h_mis)
    v_count = sum(sum(row) for row in v_mis)
    return h_count + v_count, h_count, v_count


def mismatch_cells_set(h_mis, v_mis):
    """Return the set of cells that have at least one mismatched edge."""
    cells = set()
    for r in range(len(h_mis)):
        for c in range(len(h_mis[0])):
            if h_mis[r][c]:
                cells.add((r, c))
                cells.add((r+1, c))
    for r in range(len(v_mis)):
        for c in range(len(v_mis[0])):
            if v_mis[r][c]:
                cells.add((r, c))
                cells.add((r, c+1))
    return cells


def connected_components(cells):
    """4-connected components on a set of (r,c) cells."""
    if not cells:
        return []
    cells = set(cells)
    visited = set()
    components = []
    for start in cells:
        if start in visited: continue
        # BFS
        queue = [start]
        component = []
        while queue:
            cur = queue.pop()
            if cur in visited: continue
            visited.add(cur)
            component.append(cur)
            r, c = cur
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                neighbor = (r+dr, c+dc)
                if neighbor in cells and neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)
    return components


def main():
    pieces = load_pieces()
    candidates = [
        ("Standing 459 (vol-60)", "output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json", 459),
        ("Vol-32 RECORD 458", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json", 458),
        ("Vol-35 RECORD TIE 458", "output/vol-35/records/RECORD_TIE_458_vol35_deep458_winning5_seed5.json", 458),
        ("Vol-35 RECORD TIE 457", "output/vol-35/records/RECORD_TIE_457_vol35_deep458_diverse_seed5_3hints.json", 457),
        ("J1-hinted-v2 ALNS s7", "output/v17_alns_only/basic_sa_t1_s7_1779025321_699358000_p14813.json", 445),
        ("J1-hinted-v2 ALNS s42", "output/v17_alns_only/basic_sa_t1_s42_1779025321_735369000_p14814.json", 444),
        ("J1-FLH 447 raw", "output/vol-122/j1_rust_flh.json", 447),
        ("J1-FLH 444 raw", "output/vol-122/j1_rust_chain.json", 444),
    ]
    print(f"\nMismatch topology:")
    print(f"{'Board':<40} {'matched':>8} {'mismatches':>10} {'#comps':>7} {'maxcomp':>8} {'avgcomp':>8}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        try:
            h_mis, v_mis = board_to_mismatch_map(path, pieces)
            total, hc, vc = count_mismatches(h_mis, v_mis)
            cells = mismatch_cells_set(h_mis, v_mis)
            comps = connected_components(cells)
            if comps:
                sizes = [len(c) for c in comps]
                maxc = max(sizes)
                avgc = sum(sizes) / len(sizes)
            else:
                maxc, avgc = 0, 0
            print(f"{label:<40} {mexpected:>8} {total:>10} {len(comps):>7} {maxc:>8} {avgc:>8.1f}")
        except Exception as e:
            print(f"{label:<40} {mexpected:>8} ERROR: {e}")


if __name__ == "__main__":
    main()
