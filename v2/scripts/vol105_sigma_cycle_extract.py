#!/usr/bin/env python3
"""Vol-105 — extract the σ-cycle decomposition between two boards and
dump the cells of each cycle, sorted by size descending.

Used to feed cluster-MIP / joint-swap-MIP with σ-cycle-derived cell
sets. The key question: if we take the 80-cell "giant cycle" of the
458→McGavin σ-map and MIP-permute pieces within those 80 cells (with
all other cells pinned to 458), can the MIP find McGavin's
permutation as the optimum?

If yes: delta = +11 (458 → 469), and we have a constructive bridge.
If no: the local-MIP objective doesn't see the global score gain, and
the rigidity theorem extends to non-contiguous cell-sets.

Usage:
    vol105_sigma_cycle_extract.py <board_a.json> <board_b.json> [--min-size 2]

Outputs: prints a JSON document with cycle_id, size, cells (positions
and xy), pieces (piece-ids in a-board ordering).
"""

import argparse
import json
import sys
from pathlib import Path


def load_board(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement") or d.get("board", {}).get("placement", [])
    pos_to_pid = {}
    pid_to_pos = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = int(item.get("pos", idx))
        pid = int(item["piece_id"])
        pos_to_pid[pos] = pid
        pid_to_pos[pid] = pos
    return {
        "pos_to_pid": pos_to_pid,
        "pid_to_pos": pid_to_pos,
        "matched": d.get("matched"),
        "path": str(p),
    }


def sigma_cycles(a, b, width=16):
    """σ: pos_in_a -> pos_in_b for each piece-id present in both."""
    s = {}
    for pos, pid in a["pos_to_pid"].items():
        bpos = b["pid_to_pos"].get(pid)
        if bpos is not None and bpos != pos:
            s[pos] = bpos
    visited = set()
    cycles = []
    for start in s:
        if start in visited:
            continue
        c = []
        cur = start
        while cur in s and cur not in visited:
            visited.add(cur)
            c.append(cur)
            cur = s[cur]
        if len(c) >= 2:
            cycles.append(c)
    return cycles


def pos_to_xy(pos, width):
    return pos % width, pos // width


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_a", help="origin board (e.g. 458)")
    ap.add_argument("board_b", help="target board (e.g. McGavin 469)")
    ap.add_argument("--min-size", type=int, default=2)
    ap.add_argument("--width", type=int, default=16)
    args = ap.parse_args()

    a = load_board(args.board_a)
    b = load_board(args.board_b)
    cycles = sigma_cycles(a, b, args.width)
    cycles.sort(key=len, reverse=True)

    out = {
        "board_a": args.board_a,
        "board_b": args.board_b,
        "a_score": a["matched"],
        "b_score": b["matched"],
        "n_cycles": len(cycles),
        "cycle_sizes": [len(c) for c in cycles],
        "hamming": sum(1 for pid in a["pid_to_pos"]
                       if a["pid_to_pos"][pid] != b["pid_to_pos"].get(pid)),
        "cycles": [],
    }
    for ci, c in enumerate(cycles):
        if len(c) < args.min_size:
            continue
        cells = []
        for pos in c:
            x, y = pos_to_xy(pos, args.width)
            cells.append({"pos": pos, "x": x, "y": y, "a_pid": a["pos_to_pid"][pos]})
        out["cycles"].append({"cycle_id": ci, "size": len(c), "cells": cells})

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
