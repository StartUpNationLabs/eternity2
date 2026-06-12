#!/usr/bin/env python3
"""Bucas URL for a (partial) board JSON, indexed or pos format.

Usage: bucas_url.py BOARD.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "v216_lp"))
import lp_prefix_score as L

PUZZLE = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                      "data", "puzzles", "size_16_official_eternity.csv")


def main():
    pieces, _ = L.load_puzzle(PUZZLE)
    pl = json.load(open(sys.argv[1]))["placement"]
    grid = {}
    for i, e in enumerate(pl):
        if e is None:
            continue
        pos = e.get("pos", i)
        grid[pos] = L.oriented(pieces[e["piece_id"]], e["rotation"])
    enc = "".join(
        "".join(chr(97 + c) for c in grid[p]) if p in grid else "aaaa"
        for p in range(256)
    )
    print(f"https://e2.bucas.name/#puzzle=Eternity2&board_w=16&board_h=16"
          f"&board_edges={enc}")


if __name__ == "__main__":
    main()
