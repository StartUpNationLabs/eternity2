#!/usr/bin/env python3
"""Vol-122 K11 corpus signatures: λ_2 + mismatch-zlib on all RECORD_TIE_* boards."""
import json
import os
import sys
import glob
import zlib

sys.path.insert(0, 'scripts')
try:
    import numpy as np
    from scipy.sparse.csgraph import laplacian
    from scipy.sparse import csr_matrix
    from vol122_fft_signature import load_pieces, rot_edges, SIDE
    from vol122_k11_4_compression import color_mismatch_bytes, load_placement
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)


def board_to_match_graph_np(board_path, pieces):
    placement = load_placement(board_path)
    n = SIDE * SIDE
    rows, cols = [], []
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None: continue
            pid, rot = placement[r][c]
            if pid >= len(pieces): continue
            T, R, B, L = rot_edges(pieces[pid], rot)
            i = r * SIDE + c
            if c + 1 < SIDE and placement[r][c+1]:
                pid2, rot2 = placement[r][c+1]
                if pid2 < len(pieces):
                    nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                    if R == nL and R != 0:
                        j = r * SIDE + (c+1)
                        rows += [i, j]; cols += [j, i]
            if r + 1 < SIDE and placement[r+1][c]:
                pid2, rot2 = placement[r+1][c]
                if pid2 < len(pieces):
                    nT, nR, nB, nL = rot_edges(pieces[pid2], rot2)
                    if B == nT and B != 0:
                        j = (r+1) * SIDE + c
                        rows += [i, j]; cols += [j, i]
    data = np.ones(len(rows))
    A = csr_matrix((data, (rows, cols)), shape=(n, n))
    return A


def lambda_2(A):
    L = laplacian(A, normed=False).toarray().astype(float)
    eigvals = np.linalg.eigvalsh(L)
    return float(eigvals[1])


def get_score(path):
    with open(path) as f: d = json.load(f)
    return d.get('matched_edges')


def main():
    pieces = load_pieces()
    boards = []
    # collect: RECORD_TIE_45*.json with placement
    paths = sorted(glob.glob("output/vol-32/RECORD*.json") +
                   glob.glob("output/vol-35/records/RECORD_TIE_45*.json") +
                   glob.glob("output/vol-34/t3_signal/RECORD_TIE_457*.json") +
                   glob.glob("output/vol-60/RECORDS/RECORD_TIE_459*.json"))
    print(f"Found {len(paths)} candidate boards")
    print(f"{'File':<70} {'score':>6} {'λ_2':>10} {'mz':>5}")
    results = []
    for p in paths:
        try:
            with open(p) as f: d = json.load(f)
            if 'placement' not in d: continue
            score = d.get('matched_edges')
            if score is None:
                # extract from filename
                fname = os.path.basename(p)
                import re
                m = re.search(r'_(\d{3})', fname)
                if m:
                    score = int(m.group(1))
                else:
                    continue
            if score < 455: continue
            A = board_to_match_graph_np(p, pieces)
            l2 = lambda_2(A)
            mb = color_mismatch_bytes(load_placement(p), pieces)
            mz = len(zlib.compress(mb, level=9))
            results.append((p, score, l2, mz))
        except Exception as e:
            print(f"  ERROR {p}: {e}")
            continue
    # sort by score then by lambda_2
    results.sort(key=lambda x: (-x[1], -x[2]))
    for p, score, l2, mz in results:
        name = p.split('/')[-1]
        print(f"  {name[:68]:<68}  {score:>5}  {l2:>10.4f}  {mz:>5}")


if __name__ == "__main__":
    main()
