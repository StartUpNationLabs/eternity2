#!/usr/bin/env python3
"""Vol-122 K11.4 — Information-theoretic compression scoring.

For each board, compute the LZ77-style compression length (or LZMA via
Python's lzma module) of multiple piece-id traversals:
- Row-major
- Col-major
- Diagonal
- Spiral

Hypothesis: high-score boards have more local-structure → better
compressibility.
"""
import json
import os
import sys
import lzma
import zlib

sys.path.insert(0, 'scripts')
SIDE = 16


def load_placement(board_path):
    with open(board_path) as f:
        data = json.load(f)
    placement = [[None] * SIDE for _ in range(SIDE)]
    for p in data['placement']:
        pos = p['pos']
        r, c = pos // SIDE, pos % SIDE
        placement[r][c] = (p['piece_id'], p['rotation'])
    return placement


def parse_color(s):
    if s == "1" * 16: return 0
    v = int(s, 2)
    if v == 0: return 0
    return v.bit_length()


def load_pieces():
    pieces = []
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        for ln in f.readlines()[1:]:
            parts = ln.strip().split(',')
            if len(parts) < 7: continue
            pieces.append((parse_color(parts[0]), parse_color(parts[1]),
                           parse_color(parts[2]), parse_color(parts[3])))
    return pieces


def rot_edges_local(e, r):
    if r == 0: return e
    if r == 1: return (e[3], e[0], e[1], e[2])
    if r == 2: return (e[2], e[3], e[0], e[1])
    return (e[1], e[2], e[3], e[0])


def color_array(placement, pieces):
    """Return a 16x16x4 array of edge colors."""
    out = bytearray()
    for r in range(SIDE):
        for c in range(SIDE):
            if placement[r][c] is None:
                out.extend([255, 255, 255, 255])
            else:
                pid, rot = placement[r][c]
                if pid >= len(pieces):
                    out.extend([255, 255, 255, 255])
                else:
                    e = rot_edges_local(pieces[pid], rot)
                    out.extend(e)
    return bytes(out)


def color_mismatch_bytes(placement, pieces):
    """Return a sequence of bytes encoding mismatch (1) or match (0) for each
    internal edge, in row-major then col-major order."""
    out = bytearray()
    for r in range(SIDE):
        for c in range(SIDE - 1):
            if placement[r][c] and placement[r][c+1]:
                pid1, rot1 = placement[r][c]
                pid2, rot2 = placement[r][c+1]
                if pid1 < len(pieces) and pid2 < len(pieces):
                    e1 = rot_edges_local(pieces[pid1], rot1)
                    e2 = rot_edges_local(pieces[pid2], rot2)
                    out.append(0 if (e1[1] == e2[3] and e1[1] != 0) else 1)
                    continue
            out.append(2)  # unknown
    for c in range(SIDE):
        for r in range(SIDE - 1):
            if placement[r][c] and placement[r+1][c]:
                pid1, rot1 = placement[r][c]
                pid2, rot2 = placement[r+1][c]
                if pid1 < len(pieces) and pid2 < len(pieces):
                    e1 = rot_edges_local(pieces[pid1], rot1)
                    e2 = rot_edges_local(pieces[pid2], rot2)
                    out.append(0 if (e1[2] == e2[0] and e1[2] != 0) else 1)
                    continue
            out.append(2)
    return bytes(out)


def to_bytes(traversal):
    """Encode a sequence of (pid, rot) as bytes: pid (1 byte) + rot (1 byte)."""
    out = bytearray()
    for cell in traversal:
        if cell is None:
            out.append(255); out.append(255)
        else:
            pid, rot = cell
            out.append(pid)
            out.append(rot)
    return bytes(out)


def row_major(placement):
    return [placement[r][c] for r in range(SIDE) for c in range(SIDE)]


def col_major(placement):
    return [placement[r][c] for c in range(SIDE) for r in range(SIDE)]


def spiral(placement):
    seen = set()
    res = []
    r, c = 0, 0
    dr, dc = 0, 1
    for _ in range(SIDE * SIDE):
        res.append(placement[r][c])
        seen.add((r, c))
        nr, nc = r + dr, c + dc
        if not (0 <= nr < SIDE and 0 <= nc < SIDE) or (nr, nc) in seen:
            dr, dc = dc, -dr
            nr, nc = r + dr, c + dc
        r, c = nr, nc
    return res


def diagonal(placement):
    res = []
    for d in range(2 * SIDE - 1):
        for r in range(SIDE):
            c = d - r
            if 0 <= c < SIDE:
                res.append(placement[r][c])
    return res


def measure(traversal):
    raw = to_bytes(traversal)
    lzma_len = len(lzma.compress(raw, preset=9))
    zlib_len = len(zlib.compress(raw, level=9))
    return lzma_len, zlib_len, len(raw)


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
    print(f"\nCompression analysis (LZMA bytes; lower = more compressible):")
    print(f"{'Board':<40} {'matched':>8} {'color-lzma':>11} {'color-zlib':>11} {'mismatch-lzma':>14} {'mismatch-zlib':>14}")
    for label, path, mexpected in candidates:
        if not os.path.exists(path):
            print(f"{label:<40} {mexpected:>8} NOT FOUND")
            continue
        placement = load_placement(path)
        ca = color_array(placement, pieces)
        cb = color_mismatch_bytes(placement, pieces)
        ca_lz = len(lzma.compress(ca, preset=9))
        ca_zl = len(zlib.compress(ca, level=9))
        cb_lz = len(lzma.compress(cb, preset=9))
        cb_zl = len(zlib.compress(cb, level=9))
        print(f"{label:<40} {mexpected:>8} {ca_lz:>11} {ca_zl:>11} {cb_lz:>14} {cb_zl:>14}")


if __name__ == "__main__":
    main()
