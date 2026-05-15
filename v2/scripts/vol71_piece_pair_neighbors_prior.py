#!/usr/bin/env python3
"""Vol-71 — Piece-pair neighbor frequency prior.

From our 135 saved 455+ records, count how often each (piece, piece)
pair appears as adjacent neighbors (any direction, any rotation).

This builds an empirical PRIOR for "good neighbors". Used as
value-order hint: when placing piece X at cell c, prefer neighboring
pieces high-frequency in the prior.

Output: 256×256 matrix of pair-neighbor counts, plus top pairs.

The TEST: this prior IGNORES McGavin's basin specifically. It learns
from our 135 record-level boards, which sample 47 basin-components.
If new high-score basins use the same neighbor patterns, the prior
helps. If they don't (McGavin's basin uses different patterns), the
prior may not help reach 470+.
"""

import collections
import csv
import json
import glob
import sys
from pathlib import Path

import numpy as np


def load_pieces():
    BORDER_RAW = 65535
    pieces = []
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        size = int(f.readline().strip())
        for idx, line in enumerate(f):
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append((col(parts[0]), col(parts[1]), col(parts[2]), col(parts[3])))
    return pieces


def load_placement(p):
    try:
        with open(p) as f: d = json.load(f)
    except: return None, None
    if not isinstance(d, dict): return None, None
    arr = d.get("placement", [])
    if not isinstance(arr, list) or len(arr) == 0: return None, None
    out = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        out[pos] = (item["piece_id"], item["rotation"])
    return out, d.get("matched")


def main():
    pieces = load_pieces()
    n_pieces = len(pieces)

    # Collect all 455+ records
    seen = set()
    boards = []
    for f in glob.glob("output/**/*.json", recursive=True):
        if "cycles.json" in f or ".log" in f or "INVALID" in f: continue
        pl, sc = load_placement(f)
        if pl is None or not isinstance(sc, int) or sc < 455: continue
        h = hash(tuple(sorted(pl.items())))
        if h in seen: continue
        seen.add(h)
        boards.append(pl)
    print(f"Records (≥ 455, unique): {len(boards)}")

    # Count pair-neighbor frequencies (undirected — adjacency is symmetric)
    pair_count = np.zeros((n_pieces, n_pieces), dtype=np.int32)
    for board in boards:
        for pos, (pid, _) in board.items():
            r, c = divmod(pos, 16)
            # Right neighbor
            if c < 15:
                npos = pos + 1
                if npos in board:
                    npid, _ = board[npos]
                    a, b = min(pid, npid), max(pid, npid)
                    pair_count[a, b] += 1
            # Below neighbor
            if r < 15:
                npos = pos + 16
                if npos in board:
                    npid, _ = board[npos]
                    a, b = min(pid, npid), max(pid, npid)
                    pair_count[a, b] += 1

    # Stats
    n_pairs_with_freq = int(np.sum(pair_count > 0))
    total_pairs = n_pieces * (n_pieces - 1) // 2
    print(f"Distinct piece-pairs as neighbors: {n_pairs_with_freq} / {total_pairs} = "
          f"{n_pairs_with_freq/total_pairs*100:.1f}%")

    # Top pairs
    flat_indices = np.argsort(-pair_count.flatten())[:30]
    print(f"\nTop 30 most-frequent neighbor pairs:")
    print(f"{'count':>5} | piece A | piece B | A edges | B edges")
    for idx in flat_indices:
        i, j = divmod(int(idx), n_pieces)
        if i >= j: continue  # upper triangle only
        cnt = pair_count[i, j]
        if cnt == 0: break
        print(f"{cnt:>5} | {i:>7} | {j:>7} | {pieces[i]} | {pieces[j]}")

    # Save
    Path("output/vol-71").mkdir(parents=True, exist_ok=True)
    np.savez("output/vol-71/pair_neighbor_freq.npz", pair_count=pair_count)
    print(f"\nSaved pair-neighbor frequency matrix to output/vol-71/pair_neighbor_freq.npz")

    # Compare to McGavin: what's McGavin's neighbor profile?
    mcg, _ = load_placement("output/vol-65/mcgavin_469.json")
    if mcg is None: return
    mcg_pairs = set()
    for pos, (pid, _) in mcg.items():
        r, c = divmod(pos, 16)
        if c < 15 and pos+1 in mcg:
            npid = mcg[pos+1][0]
            mcg_pairs.add((min(pid, npid), max(pid, npid)))
        if r < 15 and pos+16 in mcg:
            npid = mcg[pos+16][0]
            mcg_pairs.add((min(pid, npid), max(pid, npid)))
    print(f"\nMcGavin uses {len(mcg_pairs)} distinct neighbor-pairs")
    # How many of McGavin's pairs are in OUR pair-prior (frequency > 0)?
    in_prior = sum(1 for (a, b) in mcg_pairs if pair_count[a, b] > 0)
    print(f"  McGavin pairs that appear in our records' priors: {in_prior} / {len(mcg_pairs)} = {100*in_prior/len(mcg_pairs):.1f}%")
    print(f"  McGavin pairs UNIQUE to him: {len(mcg_pairs) - in_prior}")


if __name__ == "__main__":
    main()
