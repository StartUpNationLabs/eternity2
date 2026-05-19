#!/usr/bin/env python3
"""V159 — Build per-corner-perm priors.

For each unique (TL_pid, TR_pid, BL_pid, BR_pid) corner-perm seen in
high-score boards (≥440), build a prior matrix from JUST those boards.

Output: scripts/v155_prior/per_basin/prior_<cp>.json
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
    if not isinstance(m, int): return None
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
    print(f"[v159] scanning {len(boards)} boards", flush=True)

    # Group by corner perm.
    by_cp = defaultdict(list)
    for bp in boards:
        result = load_board(bp, N)
        if result is None: continue
        m, placement = result
        if m < args.threshold: continue
        cp = tuple(placement[c][0] for c in (0, N-1, N*(N-1), N*N-1))
        by_cp[cp].append((m, placement, bp.name))

    print(f"[v159] {len(by_cp)} unique corner perms at threshold {args.threshold}", flush=True)

    out_dir = REPO / "scripts/v155_prior/per_basin"
    out_dir.mkdir(exist_ok=True)
    manifest = {}
    for cp, entries in sorted(by_cp.items(), key=lambda x: -len(x[1])):
        if len(entries) < 3:
            continue  # too few; useless prior
        max_m = max(e[0] for e in entries)
        cp_str = "_".join(str(c) for c in cp)
        matrix = [[0] * N*N for _ in range(256)]
        for m, placement, _ in entries:
            for pos, cell in enumerate(placement):
                pid, _ = cell
                matrix[pid][pos] += 1
        out_path = out_dir / f"prior_cp{cp_str}.json"
        json.dump({
            "n_pieces": 256,
            "n_positions": N*N,
            "n_boards": len(entries),
            "corner_perm": list(cp),
            "max_score": max_m,
            "matrix": matrix,
        }, open(out_path, "w"))
        manifest[cp_str] = {"n_boards": len(entries), "max_score": max_m, "path": str(out_path.relative_to(REPO))}
        print(f"  cp={cp}: {len(entries)} boards, max_score={max_m} → {out_path.name}")

    json.dump(manifest, open(out_dir / "manifest.json", "w"), indent=2)
    print(f"[v159] {len(manifest)} per-basin priors saved")


if __name__ == "__main__":
    main()
