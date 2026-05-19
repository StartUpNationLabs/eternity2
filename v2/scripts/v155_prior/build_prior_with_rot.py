#!/usr/bin/env python3
"""V155-T2 — Build rotation-aware prior: (piece_id, rotation, position).

Output: scripts/v155_prior/prior_matrix_with_rot.json
  3D tensor flattened: matrix[piece_id * N_ROT + rotation][position] = count.

This is 1024×256 = 262144 entries vs the original 256×256 = 65536.
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_board(path, size=16):
    try:
        d = json.load(open(path))
    except Exception:
        return None
    m = d.get("matched")
    pl = d.get("placement", [])
    if not isinstance(m, int):
        return None
    has_pos = any(isinstance(e, dict) and "pos" in e for e in pl)
    placement = [None] * (size * size)
    if has_pos:
        for entry in pl:
            if isinstance(entry, dict):
                placement[int(entry["pos"])] = (int(entry["piece_id"]), int(entry["rotation"]))
    else:
        for i, entry in enumerate(pl):
            if isinstance(entry, dict):
                placement[i] = (int(entry["piece_id"]), int(entry["rotation"]))
    if not all(c is not None for c in placement):
        return None
    return m, placement


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=int, default=440)
    ap.add_argument("--size", type=int, default=16)
    args = ap.parse_args()

    db = REPO / "database-400-480"
    boards = sorted(db.glob("*.json"))
    print(f"[v155-t2] scanning {len(boards)} board files", flush=True)

    n_pieces = 256
    n_rot = 4
    n_positions = args.size * args.size
    # matrix[pid * n_rot + rot][pos] = count
    matrix = [[0] * n_positions for _ in range(n_pieces * n_rot)]
    n_included = 0

    for bp in boards:
        result = load_board(bp, args.size)
        if result is None: continue
        m, placement = result
        if m < args.threshold:
            continue
        n_included += 1
        for pos, cell in enumerate(placement):
            if cell is None: continue
            pid, rot = cell
            matrix[pid * n_rot + rot][pos] += 1

    print(f"[v155-t2] included {n_included} boards (score >= {args.threshold})")
    nonzero = sum(1 for row in matrix for v in row if v > 0)
    print(f"[v155-t2] {nonzero}/{n_pieces*n_rot*n_positions} (pid,rot,pos) cells have ≥1 occurrence")
    flat = sorted([v for row in matrix for v in row], reverse=True)
    print(f"[v155-t2] top frequencies: {flat[:10]}")
    print(f"[v155-t2] mean: {sum(flat)/len(flat):.2f}")

    out = REPO / "scripts/v155_prior/prior_matrix_with_rot.json"
    json.dump({
        "n_pieces": n_pieces,
        "n_rotations": n_rot,
        "n_positions": n_positions,
        "n_boards": n_included,
        "threshold": args.threshold,
        "matrix": matrix,
    }, open(out, "w"))
    print(f"[v155-t2] saved to {out}")


if __name__ == "__main__":
    main()
