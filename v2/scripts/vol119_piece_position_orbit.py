#!/usr/bin/env python3
"""Vol-119 — piece-position orbit analysis.

For each piece, find all (position, rotation) values seen across the corpus.
A piece with MANY observed positions is "wandery"; one with FEW is "locked".

If a piece appears at only one position across all 30 basins, that's a
near-deterministic placement. Locked pieces define a "skeleton" — and
the unlocked ones define the search basin.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_board(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    out = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        out[pos] = (int(item["piece_id"]), int(item["rotation"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("boards", nargs="+")
    args = ap.parse_args()

    files = []
    for p in args.boards:
        pp = Path(p)
        if pp.is_dir():
            files.extend(pp.glob("*.json"))
        else:
            files.append(pp)
    files = sorted(set(files))

    boards = []
    for f in files:
        try:
            b = load_board(f)
            if len(b) >= 200:
                boards.append((f, b))
        except Exception as e:
            print(f"skip {f}: {e}")
    print(f"# {len(boards)} boards loaded")

    # piece_id -> set of positions
    piece_positions = defaultdict(set)
    piece_observations = defaultdict(int)
    for f, b in boards:
        for pos, (pid, rot) in b.items():
            piece_positions[pid].add(pos)
            piece_observations[pid] += 1

    pos_per_piece = {pid: len(s) for pid, s in piece_positions.items()}
    distribution = defaultdict(int)
    for pid, n in pos_per_piece.items():
        distribution[n] += 1

    print(f"\n# Piece-position orbit distribution:")
    print(f"# positions_per_piece -> # pieces with that orbit size")
    for n in sorted(distribution):
        print(f"  {n}: {distribution[n]}")

    # Locked pieces (orbit size = 1):
    locked = [pid for pid, n in pos_per_piece.items() if n == 1]
    print(f"\n# Locked pieces (orbit size = 1): {len(locked)}")
    print(f"# Mean orbit size: {sum(pos_per_piece.values())/len(pos_per_piece):.1f}")

    # By piece class:
    # Corners: 4 corner pieces. Borders: 56 edge pieces. Interior: 196 pieces.
    # We can't identify class from id directly. Estimate by checking how many
    # positions are border/corner.

    # Print top 10 most-locked + least-locked
    sorted_pieces = sorted(pos_per_piece.items(), key=lambda x: x[1])
    print(f"\n# 10 most-locked pieces (least position diversity):")
    for pid, n in sorted_pieces[:10]:
        positions = sorted(piece_positions[pid])
        print(f"  pid={pid}: {n} positions, e.g. {positions[:5]}")

    print(f"\n# 10 least-locked pieces (most diverse):")
    for pid, n in sorted_pieces[-10:]:
        positions = sorted(piece_positions[pid])
        print(f"  pid={pid}: {n} positions, e.g. {positions[:5]}")


if __name__ == "__main__":
    main()
