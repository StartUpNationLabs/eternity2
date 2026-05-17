#!/usr/bin/env python3
"""Vol-122 — combined cross-domain score.

Sum normalized contributions from each metric. Ranks 14 record boards
by structural quality, with the goal of identifying boards that combine
both 'local matching' and 'global connectivity'.

Normalization: each metric is z-scored across all candidates.
Sign: lower-is-better metrics are negated.
"""
import os
import sys
import json
import glob
import zlib

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import laplacian
    from e2_io import load_pieces, rot_edges, load_placement, SIDE, score_board
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def build_match_adjacency(placement, pieces):
    n = SIDE * SIDE
    rows, cols = [], []
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            pid, rot = placement[r][c]
            T, R, B, L = rot_edges(pieces[pid], rot)
            i = r * SIDE + c
            if c + 1 < SIDE and placement[r][c+1] is not None:
                pid2, rot2 = placement[r][c+1]
                nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                if R == nL and R != 0:
                    rows += [i, r*SIDE+(c+1)]; cols += [r*SIDE+(c+1), i]
            if r + 1 < SIDE and placement[r+1][c] is not None:
                pid2, rot2 = placement[r+1][c]
                nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                if B == nT and B != 0:
                    rows += [i, (r+1)*SIDE+c]; cols += [(r+1)*SIDE+c, i]
    A_sparse = csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    return A_sparse


def compute_metrics(board_path, pieces):
    placement = load_placement(board_path)
    A = build_match_adjacency(placement, pieces)
    A_dense = A.toarray()
    n = A_dense.shape[0]
    # λ_2
    L = laplacian(A, normed=False).toarray()
    eigvals = np.linalg.eigvalsh(L)
    lambda_2 = float(eigvals[1])
    # mismatch zlib
    out = bytearray()
    for r in range(SIDE):
        for c in range(SIDE-1):
            cell1 = placement[r][c]; cell2 = placement[r][c+1]
            if cell1 and cell2:
                e1 = rot_edges(pieces[cell1[0]], cell1[1])
                e2 = rot_edges(pieces[cell2[0]], cell2[1])
                out.append(0 if (e1[1] == e2[3] and e1[1] != 0) else 1)
            else: out.append(2)
    for c in range(SIDE):
        for r in range(SIDE-1):
            cell1 = placement[r][c]; cell2 = placement[r+1][c]
            if cell1 and cell2:
                e1 = rot_edges(pieces[cell1[0]], cell1[1])
                e2 = rot_edges(pieces[cell2[0]], cell2[1])
                out.append(0 if (e1[2] == e2[0] and e1[2] != 0) else 1)
            else: out.append(2)
    mz = len(zlib.compress(bytes(out), level=9))
    # Effective resistance among 4 corners
    corners_i = [0, SIDE-1, SIDE*(SIDE-1), SIDE*SIDE-1]
    L_pinv = np.linalg.pinv(L)
    diag = np.diag(L_pinv)
    r_eff = []
    for i in corners_i:
        for j in corners_i:
            if j > i:
                r_eff.append(diag[i] + diag[j] - 2 * L_pinv[i][j])
    avg_r_eff = float(np.mean(r_eff))
    # Count faces
    edges_set = set()
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            T, R, B, L_e = rot_edges(pieces[placement[r][c][0]], placement[r][c][1])
            i = r * SIDE + c
            if c + 1 < SIDE and placement[r][c+1]:
                p2, rot2 = placement[r][c+1]
                e2 = rot_edges(pieces[p2], rot2)
                if R == e2[3] and R != 0:
                    edges_set.add((min(i, r*SIDE+(c+1)), max(i, r*SIDE+(c+1))))
            if r + 1 < SIDE and placement[r+1][c]:
                p2, rot2 = placement[r+1][c]
                e2 = rot_edges(pieces[p2], rot2)
                if B == e2[0] and B != 0:
                    edges_set.add((min(i, (r+1)*SIDE+c), max(i, (r+1)*SIDE+c)))
    faces = 0
    for r in range(SIDE - 1):
        for c in range(SIDE - 1):
            tl = r * SIDE + c
            tr = r * SIDE + (c+1)
            bl = (r+1) * SIDE + c
            br = (r+1) * SIDE + (c+1)
            if all(((min(a, b), max(a, b)) in edges_set) for a, b in [(tl,tr),(tr,br),(bl,br),(tl,bl)]):
                faces += 1
    return {
        'lambda_2': lambda_2,
        'mz': mz,
        'r_eff': avg_r_eff,
        'faces': faces,
    }


def main():
    pieces = load_pieces()
    paths = sorted(glob.glob("output/vol-32/RECORD*.json") +
                   glob.glob("output/vol-35/records/RECORD_TIE_45*.json") +
                   glob.glob("output/vol-34/t3_signal/RECORD_TIE_457*.json") +
                   glob.glob("output/vol-60/RECORDS/RECORD_TIE_459*.json"))
    rows = []
    for p in paths:
        try:
            placement = load_placement(p)
            matched, total = score_board(placement, pieces)
            if matched < 455: continue
            metrics = compute_metrics(p, pieces)
            rows.append({'path': p, 'matched': matched, **metrics})
        except Exception as e:
            print(f"  ERROR {p}: {e}")
    if not rows:
        print("No boards processed.")
        return

    # Normalize metrics (z-score)
    lambdas = np.array([r['lambda_2'] for r in rows])
    mzs = np.array([r['mz'] for r in rows])
    reff = np.array([r['r_eff'] for r in rows])
    faces = np.array([r['faces'] for r in rows])

    def z(x): return (x - x.mean()) / (x.std() + 1e-9)

    # Combined score: higher-is-better metrics get +z; lower-is-better get -z
    for i, r in enumerate(rows):
        z_lambda = (r['lambda_2'] - lambdas.mean()) / (lambdas.std() + 1e-9)
        z_mz = -(r['mz'] - mzs.mean()) / (mzs.std() + 1e-9)  # lower better
        z_reff = -(r['r_eff'] - reff.mean()) / (reff.std() + 1e-9)  # lower better
        z_faces = (r['faces'] - faces.mean()) / (faces.std() + 1e-9)  # higher better
        r['combined'] = z_lambda + z_mz + z_reff + z_faces

    rows.sort(key=lambda x: x['combined'], reverse=True)
    print(f"{'name':<60} {'matched':>7} {'λ_2':>7} {'mz':>4} {'R_eff':>7} {'faces':>5} {'combined':>8}")
    for r in rows:
        name = os.path.basename(r['path'])
        print(f"  {name[:58]:<58}  {r['matched']:>5}  {r['lambda_2']:>7.4f}  {r['mz']:>4}  {r['r_eff']:>7.4f}  {r['faces']:>5}  {r['combined']:>+8.3f}")


if __name__ == "__main__":
    main()
