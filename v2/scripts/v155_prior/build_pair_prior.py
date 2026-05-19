#!/usr/bin/env python3
"""V155-T3 — Build piece-pair prior: P(piece p1, piece p2 are H-neighbors)
and P(piece p1, piece p2 are V-neighbors).

Output format: scripts/v155_prior/pair_prior.json
  {
    "h_pair": [[count_p1_p2_h, ...], ...]  # 256x256 ints
    "v_pair": [[count_p1_p2_v, ...], ...]  # 256x256 ints
    "n_boards": int
  }

For each high-score board:
  - For each horizontal-adjacent (cell_y_x, cell_y_x+1) pair: increment h_pair[p1][p2]
    where p1 = piece at (y, x), p2 = piece at (y, x+1).
  - Similarly for vertical (cell_y_x, cell_y+1_x): v_pair[p1][p2].
"""
from __future__ import annotations
import argparse
import json
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
    N = args.size

    db = REPO / "database-400-480"
    boards = sorted(db.glob("*.json"))
    print(f"[v155-t3] scanning {len(boards)} boards", flush=True)

    n_pieces = 256
    h_pair = [[0] * n_pieces for _ in range(n_pieces)]
    v_pair = [[0] * n_pieces for _ in range(n_pieces)]
    n_included = 0

    for bp in boards:
        result = load_board(bp, N)
        if result is None: continue
        m, placement = result
        if m < args.threshold: continue
        n_included += 1
        # Horizontal pairs
        for y in range(N):
            for x in range(N - 1):
                p1 = placement[y * N + x][0]
                p2 = placement[y * N + x + 1][0]
                h_pair[p1][p2] += 1
        # Vertical pairs
        for y in range(N - 1):
            for x in range(N):
                p1 = placement[y * N + x][0]
                p2 = placement[(y + 1) * N + x][0]
                v_pair[p1][p2] += 1

    print(f"[v155-t3] included {n_included} boards (>= {args.threshold})")

    # Stats.
    h_flat = sorted([v for row in h_pair for v in row], reverse=True)
    v_flat = sorted([v for row in v_pair for v in row], reverse=True)
    print(f"[v155-t3] h_pair: nonzero={sum(1 for v in h_flat if v>0)}/{n_pieces**2}, top: {h_flat[:5]}")
    print(f"[v155-t3] v_pair: nonzero={sum(1 for v in v_flat if v>0)}/{n_pieces**2}, top: {v_flat[:5]}")

    out = REPO / "scripts/v155_prior/pair_prior.json"
    json.dump({
        "n_pieces": n_pieces,
        "n_boards": n_included,
        "threshold": args.threshold,
        "h_pair": h_pair,
        "v_pair": v_pair,
    }, open(out, "w"))
    print(f"[v155-t3] saved to {out}")


if __name__ == "__main__":
    main()
