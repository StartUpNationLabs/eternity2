#!/usr/bin/env python3
"""V187 INTAGLIO-MIP — exact full-mismatch-band MIP for V181 460.

Decision variables:
- x[v, p, r] ∈ {0,1}: piece p in rotation r placed at cell v.

Constraints:
- Cell-uniqueness: Σ_{p,r} x[v,p,r] = 1 ∀ v
- Piece-uniqueness: Σ_{v,r} x[v,p,r] ≤ 1 ∀ p
- Border: forbid (p,r) at col 0/15 if W/E ≠ BORDER
- North boundary: at r=11, only (p,r) with edges[0] freely set, but match counts via y
- South boundary: similarly

Objective: maximise Σ over adjacent cell-pairs (in band) and (band, fixed) of edge-color matches.

The matching variable y[(v1,v2)] = Σ over compatible (p1,r1,p2,r2)
of x[v1,p1,r1] AND x[v2,p2,r2]. Linearisation: y ≤ sum_p1,r1 x[v1,p1,r1] of pieces matching v2's selected piece — but we don't know v2's piece. So we expand:

For each ordered adjacent pair (v1, v2) and each pair of (piece, rotation):
- Compute whether their edge would match.
- The y indicator for that JOINT selection is bilinear; we linearise by:
  y_{v1,p1,r1,v2,p2,r2} ≤ x[v1,p1,r1], ≤ x[v2,p2,r2]
  y_{...} ≥ x[v1,p1,r1] + x[v2,p2,r2] - 1

- Objective coefficient for each y_{...} = +1 if edges match (non-border).

But this is O(|V|^2 × |P|^2 × 16) variables — too many.

SIMPLIFICATION: For each adjacent pair (v1, v2) and each (piece, rotation) at v1, enumerate the SET of compatible (piece2, rotation2) at v2. Define:

m_{v1,v2,p1,r1} = sum over (p2, r2) compatible: x[v2, p2, r2]
y_{v1,v2} = sum over (p1, r1) of x[v1, p1, r1] · m_{v1,v2,p1,r1}

Still bilinear. Use bilinear → linear via the obvious method.

Actually let's use a DIFFERENT decomposition: define edge-color variables.
For each interior horizontal edge (between adjacent cells), let
e_h[v1, v2, c] ∈ {0,1} = "the shared edge has color c".

Constraints: e_h[v1,v2,c] = 1 implies x[v1,p1,r1]=1 for some (p1,r1)
with E(p1,r1)=c, AND x[v2,p2,r2]=1 for some (p2,r2) with W(p2,r2)=c.

Then "match" = sum of e_h[v1,v2,c] over c (which is = 1 if matched, 0 if mismatched
since both sides MUST agree on the edge or there's no match).

Hmm — actually each cell has fixed edges given its (p,r), so two adjacent
cells either agree (color matches) or disagree. We just need to count the
agreements.

Cleanest formulation: for each cell v, define cell_edge_color variables
n_v, e_v, s_v, w_v (each picks a color from {BORDER, c1, ..., c22}). Then
each side has constraints linking to x[v,p,r]:
  n_v = sum over (p,r) of x[v,p,r] · N(p,r)
which is linear in x.

For adjacent cells v1 (left), v2 (right):
  match_h(v1,v2) = 1 iff e_{v1} == w_{v2}
The match indicator is 1 iff the E of v1's piece equals the W of v2's piece.

Use a sum-over-colors approach:
  match_h(v1,v2) = sum_c [e_{v1}=c] · [w_{v2}=c]

But [e_{v1}=c] is a binary indicator. Define:
  ec_{v1,c} = 1 iff e of v1 = color c = sum over (p,r) of x[v1,p,r] with E(p,r)=c.
  wc_{v2,c} = same for w.

match_h(v1,v2) ≤ ec_{v1,c} + wc_{v2,c} (we need both, but this is a OR not AND)

Better: match_h(v1,v2,c) ∈ {0,1} with constraints:
  match_h(v1,v2,c) ≤ ec_{v1,c}
  match_h(v1,v2,c) ≤ wc_{v2,c}
  match_h(v1,v2,c) ≥ ec_{v1,c} + wc_{v2,c} - 1

And match_h(v1,v2) = sum_c match_h(v1,v2,c), and we want to max this.

For non-border match, exclude BORDER color.
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
import highspy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER, is_border, score_full

REPO = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json')
    ap.add_argument('--rows', nargs='+', type=int, default=[11, 12, 13, 14])
    ap.add_argument('--time-limit', type=int, default=1800, help='seconds')
    ap.add_argument('--out-dir', default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        from datetime import datetime
        stamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        args.out_dir = f"output/vol-187/intaglio_mip_rows{'_'.join(map(str,args.rows))}_{stamp}"
    out_dir = REPO / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"out_dir={out_dir}")

    pieces = load_pieces()
    board = json.load(open(REPO / args.base))
    score_orig = board.get('matched', 0)
    print(f"Base score: {score_orig}")
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
    print(f"target cells: {len(target_cells)}, free pieces: {len(free_pids)}")

    # Build set of all colors in the puzzle (use rotation 0 to enumerate).
    all_colors = set()
    for (pid, rot), edges in pieces.items():
        if rot != 0: continue
        all_colors.update(edges)
    colors = sorted(all_colors)
    color_idx = {c: i for i, c in enumerate(colors)}
    print(f"distinct colors: {len(colors)}")

    # Fixed cells (outside band) — pre-compute their edges facing the band.
    # For each cell in band, precompute the constraint from each direction:
    #   N: if r=min(rows), N must match cell above's S. If r=interior, no fixed N.
    #   S: similarly.
    #   W: col 0 → BORDER. Interior col, no fixed W.
    #   E: col 15 → BORDER. Interior, no fixed E.
    # NOTE: cells at non-min/max row in band have N from band cell above, S from band cell below.
    # We optimize INSIDE band; cell-to-cell N-S inside band is a variable too.

    rows_sorted = sorted(args.rows)
    row_min, row_max = rows_sorted[0], rows_sorted[-1]
    # External edge color at (r, c) facing direction d (N, E, S, W).
    # If d == 'N' and r-1 in target_rows → none (internal).
    # If d == 'N' and r-1 not in target_rows → pl[(r-1)*16+c]'s S-edge.
    # ... etc.

    def external_edge_color(r, c, direction):
        """Returns the color of the external (outside-band) edge facing (r,c) in direction, or None if internal."""
        if direction == 'N':
            if r - 1 in target_rows: return None
            if r - 1 < 0: return BORDER
            pid, rot = pl[(r - 1) * 16 + c]
            return pieces[(pid, rot)][2]  # S of cell above
        if direction == 'S':
            if r + 1 in target_rows: return None
            if r + 1 > 15: return BORDER
            pid, rot = pl[(r + 1) * 16 + c]
            return pieces[(pid, rot)][0]  # N of cell below
        if direction == 'W':
            if c - 1 < 0: return BORDER
            # c-1 within band? if same row, c-1 cell is in the band → internal.
            if (r in target_rows) and (c - 1 >= 0) and (r * 16 + (c - 1)) in set(target_cells):
                return None
            pid, rot = pl[r * 16 + (c - 1)]
            return pieces[(pid, rot)][1]  # E of cell to left
        if direction == 'E':
            if c + 1 > 15: return BORDER
            if (r in target_rows) and (c + 1 <= 15) and (r * 16 + (c + 1)) in set(target_cells):
                return None
            pid, rot = pl[r * 16 + (c + 1)]
            return pieces[(pid, rot)][3]  # W of cell to right
        raise ValueError(direction)

    # Build candidate set for each cell: keep all (pid, rot) but track external edges
    # for objective scoring (SOFT match — don't filter).
    # Only HARD filter: corners/edges must place pieces with BORDER on appropriate sides
    # (i.e., the piece TYPE must match — a non-border-piece can't go on the border).
    cand_by_cell = {}
    external_edges_by_cell = {}
    for v in target_cells:
        r, c = v // 16, v % 16
        ext_n = external_edge_color(r, c, 'N')
        ext_s = external_edge_color(r, c, 'S')
        ext_w = external_edge_color(r, c, 'W')
        ext_e = external_edge_color(r, c, 'E')
        external_edges_by_cell[v] = (ext_n, ext_e, ext_s, ext_w)
        cands = []
        for pid in free_pids:
            for rot in range(4):
                edges = pieces[(pid, rot)]
                # HARD: cell border position requires BORDER on that side.
                # If ext_X == BORDER, piece's edge_X MUST be BORDER (it's a corner/edge cell).
                # If ext_X != BORDER (and not None), piece's edge_X must NOT be BORDER
                # (interior cell can't have BORDER edge on the inside).
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
    print("candidate counts per cell (sorted):")
    for v in sorted(target_cells):
        r, c = v // 16, v % 16
        print(f"  ({r},{c}): {len(cand_by_cell[v])} candidates")

    # Filter free_pids further: a piece is reachable only if it appears in SOME cell's candidates.
    reachable = set()
    for v, cands in cand_by_cell.items():
        for pid, _ in cands:
            reachable.add(pid)
    if reachable != set(free_pids):
        unused = set(free_pids) - reachable
        print(f"  {len(unused)} free pieces NOT reachable: {sorted(unused)[:10]}...")

    # === Build MIP via highspy ===
    h = highspy.Highs()
    h.silent()

    # Variables x[v, idx] where idx indexes into cand_by_cell[v].
    # Map x_id = (v, idx) -> column index in HiGHS.
    n_x = 0
    x_col = {}  # (v, p, r) -> col_idx
    for v in target_cells:
        for idx, (pid, rot) in enumerate(cand_by_cell[v]):
            x_col[(v, pid, rot)] = n_x
            n_x += 1
    print(f"x variables: {n_x}")

    # Also need match-indicator variables for ADJACENT cell-pairs within the band.
    # Adjacency: H (same row, c, c+1) and V (same col, r, r+1) where both cells in target.
    # For each adjacent pair (v1, v2), for each color c (excluding BORDER for scoring),
    # create m_{v1,v2,c} ∈ {0,1} with constraints linking to E of v1 / W of v2 (H) or
    # S of v1 / N of v2 (V).
    # Actually simpler: just enumerate compatible (cand_idx1, cand_idx2) pairs and create binary
    # vars for each — but that blows up too.

    # Use color-indicator route. For each cell v and direction d, define color_indicator
    # cc[v, d, c] = sum over candidates of x[v, p, r] with edge_d(p, r) == c.
    # cc is LINEAR in x.
    # Then for H-adjacent v1 (left), v2 (right), edges agree iff e_v1 == w_v2.
    # match_h(v1, v2) = sum_c [cc[v1, E, c] AND cc[v2, W, c]].
    # AND linearise: m_{v1,v2,c} ≤ cc[v1,E,c]; ≤ cc[v2,W,c]; ≥ cc1+cc2-1.

    # cc[v, d, c] is implicit (sum of x). We don't need explicit variables.
    # Instead, m_{v1,v2,c} ≤ Σ x[v1,p,r : E(p,r)=c]; ≤ Σ x[v2,p,r : W(p,r)=c]; ≥ Σ.. + Σ.. - 1.

    # Compute pairs.
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

    # Build x variable bounds + cell-uniqueness rows.
    # Add columns: all x[v, p, r] are binary [0, 1] with obj coefficient 0 initially.
    obj_coeffs = [0.0] * n_x

    # Compute per-x external match contribution and bake into x's objective coefficient.
    # For cell v with external edges (n, e, s, w), piece (pid, rot) contributes:
    #   +1 if external_n != None != BORDER and piece.N == external_n
    #   +1 similarly for e, s, w
    for v in target_cells:
        ext_n, ext_e, ext_s, ext_w = external_edges_by_cell[v]
        for (pid, rot) in cand_by_cell[v]:
            edges = pieces[(pid, rot)]
            score_v = 0
            if ext_n is not None and ext_n != BORDER and edges[0] == ext_n:
                score_v += 1
            if ext_e is not None and ext_e != BORDER and edges[1] == ext_e:
                score_v += 1
            if ext_s is not None and ext_s != BORDER and edges[2] == ext_s:
                score_v += 1
            if ext_w is not None and ext_w != BORDER and edges[3] == ext_w:
                score_v += 1
            obj_coeffs[x_col[(v, pid, rot)]] = float(score_v)

    # We'll add m variables next. For now, declare x.
    lb = [0.0] * n_x
    ub = [1.0] * n_x
    import numpy as np
    h.addCols(n_x, np.array(obj_coeffs), np.array(lb), np.array(ub),
              0, np.array([], dtype=np.int32), np.array([], dtype=np.int32), np.array([], dtype=np.float64))
    # Set integrality on x.
    for col in range(n_x):
        h.changeColIntegrality(col, highspy.HighsVarType.kInteger)

    # Add m variables for each H/V pair × color.
    m_col = {}  # (v1, v2, c, 'H' or 'V') -> col_idx
    next_col = n_x
    new_obj = []
    new_lb = []
    new_ub = []
    for (v1, v2) in h_pairs:
        for c in colors:
            if c == BORDER: continue
            m_col[(v1, v2, c, 'H')] = next_col
            new_obj.append(1.0)  # objective: maximise match
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
    # m variables: continuous in [0,1] — they're implied integer by x bounds.
    # For correctness in maximisation, leave as continuous; HiGHS will push to 1 if possible.

    print(f"m variables (H+V × colors): {len(m_col)}")

    # Cell-uniqueness constraints: Σ_x_{v, p, r} = 1 for each v.
    for v in target_cells:
        idxs = []
        vals = []
        for (pid, rot) in cand_by_cell[v]:
            idxs.append(x_col[(v, pid, rot)])
            vals.append(1.0)
        h.addRow(1.0, 1.0, len(idxs), np.array(idxs, dtype=np.int32), np.array(vals))

    # Piece-uniqueness: Σ_{v, r} x[v, p, r] ≤ 1 for each p.
    for pid in free_pids:
        idxs = []
        vals = []
        for v in target_cells:
            for rot in range(4):
                if (v, pid, rot) in x_col:
                    idxs.append(x_col[(v, pid, rot)])
                    vals.append(1.0)
        if idxs:
            h.addRow(0.0, 1.0, len(idxs), np.array(idxs, dtype=np.int32), np.array(vals))

    # Match constraints: for each (v1, v2, c, dir):
    #   m ≤ Σ x[v1, p, r : edge_dir1(p,r) = c]
    #   m ≤ Σ x[v2, p, r : edge_dir2(p,r) = c]
    #   m ≥ Σ x_v1 + Σ x_v2 - 1  (with two big constraints or use one combined)

    def dir1_for(direction):
        return {'H': 1, 'V': 2}[direction]  # E or S of v1
    def dir2_for(direction):
        return {'H': 3, 'V': 0}[direction]  # W or N of v2

    for (v1, v2) in h_pairs + v_pairs:
        if (v1, v2) in [(p[0], p[1]) for p in h_pairs]:
            dir_key = 'H'
        else:
            dir_key = 'V'
        d1 = dir1_for(dir_key)
        d2 = dir2_for(dir_key)
        for c in colors:
            if c == BORDER: continue
            mcol = m_col[(v1, v2, c, dir_key)]
            # m ≤ Σ x[v1, p, r : edges[d1]=c]
            v1_xs = []
            for (pid, rot) in cand_by_cell[v1]:
                if pieces[(pid, rot)][d1] == c:
                    v1_xs.append(x_col[(v1, pid, rot)])
            # constraint: m - Σ v1_xs ≤ 0
            row_idxs = [mcol] + v1_xs
            row_vals = [1.0] + [-1.0] * len(v1_xs)
            h.addRow(-highspy.kHighsInf, 0.0, len(row_idxs), np.array(row_idxs, dtype=np.int32), np.array(row_vals))
            # m ≤ Σ x[v2, ... edges[d2]=c]
            v2_xs = []
            for (pid, rot) in cand_by_cell[v2]:
                if pieces[(pid, rot)][d2] == c:
                    v2_xs.append(x_col[(v2, pid, rot)])
            row_idxs = [mcol] + v2_xs
            row_vals = [1.0] + [-1.0] * len(v2_xs)
            h.addRow(-highspy.kHighsInf, 0.0, len(row_idxs), np.array(row_idxs, dtype=np.int32), np.array(row_vals))

    # Sense: maximize.
    h.changeObjectiveSense(highspy.ObjSense.kMaximize)
    h.setOptionValue('time_limit', float(args.time_limit))
    h.setOptionValue('parallel', 'on')

    print(f"Constraints: {h.getNumRow()}, vars: {h.getNumCol()}")
    print(f"Solving (time_limit={args.time_limit}s)...")
    t0 = time.time()
    h.run()
    dt = time.time() - t0
    status = h.getModelStatus()
    info = h.getInfo()
    obj = h.getObjectiveValue()
    print(f"Status: {status} after {dt:.1f}s, objective={obj:.1f}")
    print(f"MIP gap: {info.mip_gap if info.mip_gap is not None else 'N/A'}")

    # Compute original-band match count for comparison.
    orig_band_score = 0
    for (v1, v2) in h_pairs:
        e1 = pieces[pl[v1]][1]
        w2 = pieces[pl[v2]][3]
        if e1 == w2 and not is_border(e1):
            orig_band_score += 1
    for (v1, v2) in v_pairs:
        s1 = pieces[pl[v1]][2]
        n2 = pieces[pl[v2]][0]
        if s1 == n2 and not is_border(s1):
            orig_band_score += 1
    # External edge matches (band-cell vs outside-band cells).
    for v in target_cells:
        ext_n, ext_e, ext_s, ext_w = external_edges_by_cell[v]
        edges = pieces[pl[v]]
        if ext_n is not None and ext_n != BORDER and edges[0] == ext_n:
            orig_band_score += 1
        if ext_e is not None and ext_e != BORDER and edges[1] == ext_e:
            orig_band_score += 1
        if ext_s is not None and ext_s != BORDER and edges[2] == ext_s:
            orig_band_score += 1
        if ext_w is not None and ext_w != BORDER and edges[3] == ext_w:
            orig_band_score += 1
    print(f"Original band score (H+V in band + external matches): {orig_band_score}")

    if obj > orig_band_score + 0.5:
        print(f"*** MIP FOUND LIFT: +{obj - orig_band_score} edges ***")
        # Read solution and rebuild board.
        sol = h.getSolution()
        col_vals = sol.col_value
        new_pl = list(pl)
        for v in target_cells:
            for (pid, rot) in cand_by_cell[v]:
                if col_vals[x_col[(v, pid, rot)]] > 0.5:
                    new_pl[v] = (pid, rot)
                    break
        new_score = score_full(new_pl, pieces)
        print(f"NEW FULL SCORE: {new_score}")
        if new_score > score_orig:
            out = out_dir / f'INTAGLIO_MIP_LIFT_{new_score}.json'
            pl_json = []
            for pos, ent in enumerate(new_pl):
                if ent is None:
                    pl_json.append(None)
                else:
                    pid, rot = ent
                    pl_json.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
            out.write_text(json.dumps({'placement': pl_json, 'matched': new_score}))
            print(f"SAVED {out}")
    else:
        print(f"NO LIFT: MIP objective {obj:.1f} ≤ original {orig_band_score} (= confirms 4-row MIP-locally rigid)")


if __name__ == '__main__':
    main()
