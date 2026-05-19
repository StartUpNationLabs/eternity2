#!/usr/bin/env python3
"""Compare our V155-discovered 460 board(s) against the 460-tier boards
already in database-400-480/. Are they NEW basins or duplicates?

Two boards are 'the same basin' if they share corner perm AND have
Hamming distance < threshold. We'll report:
  - Corner perm of our board.
  - Closest existing board(s) by Hamming distance on (piece_id, position).
  - Whether identical (Hamming=0) or distinct.
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


def hamming_pid(p1, p2):
    return sum(1 for a, b in zip(p1, p2) if a[0] != b[0])


def hamming_pidrot(p1, p2):
    return sum(1 for a, b in zip(p1, p2) if a != b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="Our discovered board JSON")
    ap.add_argument("--min-score", type=int, default=459,
                    help="Only compare against DB boards with at least this score")
    args = ap.parse_args()

    target = load_board(args.target)
    if target is None:
        print(f"failed to load {args.target}")
        return
    target_score, target_pl = target
    target_cp = tuple(target_pl[c][0] for c in (0, 15, 240, 255))
    print(f"=== Target ({args.target}) ===")
    print(f"  score={target_score}")
    print(f"  corner_perm={target_cp}")
    print()

    db = REPO / "database-400-480"
    boards = sorted(db.glob("*.json"))

    matches = []
    for bp in boards:
        result = load_board(bp)
        if result is None: continue
        m, pl = result
        if m < args.min_score: continue
        cp = tuple(pl[c][0] for c in (0, 15, 240, 255))
        h_pid = hamming_pid(target_pl, pl)
        h_full = hamming_pidrot(target_pl, pl)
        matches.append((bp.name, m, cp, h_pid, h_full))

    print(f"=== {len(matches)} DB boards with score ≥ {args.min_score} ===")
    print(f"corner_perm matches:")
    same_cp = [m for m in matches if m[2] == target_cp]
    print(f"  {len(same_cp)} boards share corner perm {target_cp}")
    print()

    print("Closest 10 by piece_id Hamming distance:")
    matches.sort(key=lambda x: x[3])
    for name, m, cp, h_pid, h_full in matches[:10]:
        same_cp_marker = "*" if cp == target_cp else " "
        print(f"  {same_cp_marker} {name[:60]:<62} score={m} cp={cp} h_pid={h_pid:>3}/256 h_full={h_full:>3}/256")

    print()
    if matches[0][3] == 0:
        print("=> IDENTICAL to an existing board (Hamming=0 on piece_id).")
    elif matches[0][3] < 10:
        print(f"=> VERY SIMILAR to existing (closest h_pid={matches[0][3]})")
    elif matches[0][3] < 50:
        print(f"=> SAME-BASIN-ADJACENT (closest h_pid={matches[0][3]}).")
    else:
        print(f"=> DISTINCT from anything in DB ≥{args.min_score} (closest h_pid={matches[0][3]}).")


if __name__ == "__main__":
    main()
