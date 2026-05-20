#!/usr/bin/env python3
"""Run LP relaxation of INTAGLIO-MIP to get tight upper bound.

If LP-UB ≤ original-band-score, then by sound LP relaxation:
- No integer solution exists above original-band-score.
- The basin is PROVEN row-band-rigid (no LP-feasible lift exists).
"""
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
import highspy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border, score_full

REPO = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json')
    ap.add_argument('--rows', nargs='+', type=int, default=[11, 12, 13])
    args = ap.parse_args()

    pieces = load_pieces()
    board = json.load(open(REPO / args.base))
    pl = [None] * 256
    for ent in board['placement']:
        if ent is not None:
            pl[ent['pos']] = (ent['piece_id'], ent['rotation'])

    target_rows = set(args.rows)
    target_cells = [r * 16 + c for r in args.rows for c in range(16)]
    used_other = set()
    for pos in range(256):
        r = pos // 16
        if r in target_rows: continue
        if pl[pos] is not None:
            used_other.add(pl[pos][0])
    free_pids = sorted(set(range(256)) - used_other)

    all_colors = set()
    for (pid, rot), edges in pieces.items():
        if rot != 0: continue
        all_colors.update(edges)
    colors = sorted(all_colors)

    def external_edge_color(r, c, direction):
        if direction == 'N':
            if r - 1 in target_rows: return None
            if r - 1 < 0: return BORDER
            pid, rot = pl[(r - 1) * 16 + c]
            return pieces[(pid, rot)][2]
        if direction == 'S':
            if r + 1 in target_rows: return None
            if r + 1 > 15: return BORDER
            pid, rot = pl[(r + 1) * 16 + c]
            return pieces[(pid, rot)][0]
        if direction == 'W':
            if c - 1 < 0: return BORDER
            if (r in target_rows) and (c - 1 >= 0) and (r * 16 + (c - 1)) in set(target_cells):
                return None
            pid, rot = pl[r * 16 + (c - 1)]
            return pieces[(pid, rot)][1]
        if direction == 'E':
            if c + 1 > 15: return BORDER
            if (r in target_rows) and (c + 1 <= 15) and (r * 16 + (c + 1)) in set(target_cells):
                return None
            pid, rot = pl[r * 16 + (c + 1)]
            return pieces[(pid, rot)][3]

    cand_by_cell = {}
    external_edges_by_cell = {}
    for v in target_cells:
        r, c = v // 16, v % 16
        ext_n = external_edge_color(r, c, 'N')
        ext_e = external_edge_color(r, c, 'E')
        ext_s = external_edge_color(r, c, 'S')
        ext_w = external_edge_color(r, c, 'W')
        external_edges_by_cell[v] = (ext_n, ext_e, ext_s, ext_w)
        cands = []
        for pid in free_pids:
            for rot in range(4):
                edges = pieces[(pid, rot)]
                if ext_n == BORDER and edges[0] != BORDER: continue
                if ext_n is not None and ext_n != BORDER and edges[0] == BORDER: continue
                if ext_e == BORDER and edges[1] != BORDER: continue
                if ext_e is not None and ext_e != BORDER and edges[1] == BORDER: continue
                if ext_s == BORDER and edges[2] != BORDER: continue
                if ext_s is not None and ext_s != BORDER and edges[2] == BORDER: continue
                if ext_w == BORDER and edges[3] != BORDER: continue
                if ext_w is not None and ext_w != BORDER and edges[3] == BORDER: continue
                cands.append((pid, rot))
        cand_by_cell[v] = cands

    n_x = 0
    x_col = {}
    for v in target_cells:
        for (pid, rot) in cand_by_cell[v]:
            x_col[(v, pid, rot)] = n_x
            n_x += 1

    obj_coeffs = [0.0] * n_x
    for v in target_cells:
        ext_n, ext_e, ext_s, ext_w = external_edges_by_cell[v]
        for (pid, rot) in cand_by_cell[v]:
            edges = pieces[(pid, rot)]
            score_v = 0
            if ext_n is not None and ext_n != BORDER and edges[0] == ext_n: score_v += 1
            if ext_e is not None and ext_e != BORDER and edges[1] == ext_e: score_v += 1
            if ext_s is not None and ext_s != BORDER and edges[2] == ext_s: score_v += 1
            if ext_w is not None and ext_w != BORDER and edges[3] == ext_w: score_v += 1
            obj_coeffs[x_col[(v, pid, rot)]] = float(score_v)

    h = highspy.Highs()
    h.silent()

    lb = [0.0] * n_x
    ub = [1.0] * n_x
    h.addCols(n_x, np.array(obj_coeffs), np.array(lb), np.array(ub),
              0, np.array([], dtype=np.int32), np.array([], dtype=np.int32), np.array([], dtype=np.float64))
    # LP: NO integrality.

    h_pairs = []
    v_pairs = []
    for r in args.rows:
        for c in range(15):
            v1, v2 = r * 16 + c, r * 16 + c + 1
            if v1 in target_cells and v2 in target_cells:
                h_pairs.append((v1, v2))
    for i in range(len(args.rows) - 1):
        ra = args.rows[i]; rb = args.rows[i + 1]
        if rb != ra + 1: continue
        for c in range(16):
            v1, v2 = ra * 16 + c, rb * 16 + c
            if v1 in target_cells and v2 in target_cells:
                v_pairs.append((v1, v2))

    m_col = {}
    next_col = n_x
    new_obj = []
    new_lb = []
    new_ub = []
    for (v1, v2) in h_pairs:
        for c in colors:
            if c == BORDER: continue
            m_col[(v1, v2, c, 'H')] = next_col
            new_obj.append(1.0)
            new_lb.append(0.0)
            new_ub.append(1.0)
            next_col += 1
    for (v1, v2) in v_pairs:
        for c in colors:
            if c == BORDER: continue
            m_col[(v1, v2, c, 'V')] = next_col
            new_obj.append(1.0)
            new_lb.append(0.0)
            new_ub.append(1.0)
            next_col += 1
    h.addCols(len(new_obj), np.array(new_obj), np.array(new_lb), np.array(new_ub),
              0, np.array([], dtype=np.int32), np.array([], dtype=np.int32), np.array([], dtype=np.float64))

    for v in target_cells:
        idxs, vals = [], []
        for (pid, rot) in cand_by_cell[v]:
            idxs.append(x_col[(v, pid, rot)])
            vals.append(1.0)
        h.addRow(1.0, 1.0, len(idxs), np.array(idxs, dtype=np.int32), np.array(vals))
    for pid in free_pids:
        idxs, vals = [], []
        for v in target_cells:
            for rot in range(4):
                if (v, pid, rot) in x_col:
                    idxs.append(x_col[(v, pid, rot)])
                    vals.append(1.0)
        if idxs:
            h.addRow(0.0, 1.0, len(idxs), np.array(idxs, dtype=np.int32), np.array(vals))

    def dir1_for(d): return {'H': 1, 'V': 2}[d]
    def dir2_for(d): return {'H': 3, 'V': 0}[d]
    h_pair_set = set(h_pairs)
    for (v1, v2) in h_pairs + v_pairs:
        dk = 'H' if (v1, v2) in h_pair_set else 'V'
        d1, d2 = dir1_for(dk), dir2_for(dk)
        for c in colors:
            if c == BORDER: continue
            mcol = m_col[(v1, v2, c, dk)]
            v1_xs = [x_col[(v1, pid, rot)] for (pid, rot) in cand_by_cell[v1] if pieces[(pid, rot)][d1] == c]
            row_idxs = [mcol] + v1_xs
            row_vals = [1.0] + [-1.0] * len(v1_xs)
            h.addRow(-highspy.kHighsInf, 0.0, len(row_idxs), np.array(row_idxs, dtype=np.int32), np.array(row_vals))
            v2_xs = [x_col[(v2, pid, rot)] for (pid, rot) in cand_by_cell[v2] if pieces[(pid, rot)][d2] == c]
            row_idxs = [mcol] + v2_xs
            row_vals = [1.0] + [-1.0] * len(v2_xs)
            h.addRow(-highspy.kHighsInf, 0.0, len(row_idxs), np.array(row_idxs, dtype=np.int32), np.array(row_vals))

    h.changeObjectiveSense(highspy.ObjSense.kMaximize)
    h.setOptionValue('solver', 'ipm')  # interior-point for LP

    t0 = time.time()
    h.run()
    dt = time.time() - t0
    obj = h.getObjectiveValue()
    print(f"LP relaxation in {dt:.1f}s: UB = {obj:.4f}")

    # Compute original-band score for reference.
    orig = 0
    for (v1, v2) in h_pairs:
        e1 = pieces[pl[v1]][1]; w2 = pieces[pl[v2]][3]
        if e1 == w2 and not is_border(e1): orig += 1
    for (v1, v2) in v_pairs:
        s1 = pieces[pl[v1]][2]; n2 = pieces[pl[v2]][0]
        if s1 == n2 and not is_border(s1): orig += 1
    for v in target_cells:
        ext_n, ext_e, ext_s, ext_w = external_edges_by_cell[v]
        edges = pieces[pl[v]]
        if ext_n is not None and ext_n != BORDER and edges[0] == ext_n: orig += 1
        if ext_e is not None and ext_e != BORDER and edges[1] == ext_e: orig += 1
        if ext_s is not None and ext_s != BORDER and edges[2] == ext_s: orig += 1
        if ext_w is not None and ext_w != BORDER and edges[3] == ext_w: orig += 1
    print(f"Original band score: {orig}")
    print(f"LP-UB - orig = {obj - orig:.2f} (positive means LP allows lift)")
    if obj < orig + 0.5:
        print("✓ LP-UB proves NO integer lift possible (basin is LP-rigid on this band)")
    else:
        print(f"LP gap: {obj - orig:.2f}; integer lift POSSIBLE up to {int(obj)}")


if __name__ == '__main__':
    main()
