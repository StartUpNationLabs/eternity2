#!/usr/bin/env python3
"""Emit a bucas viewer URL for the saved v12 5-min run board.

Reads:
  - canonical puzzle: ../data/puzzles/size_16_official_eternity.csv
  - saved board:      output/v12_run/run_e2_5min_board.json
Writes the URL to stdout AND appends it to the run log.
"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v11_load_e2 as loader   # gives us the 256-piece canonical CSV → ndarray

import numpy as np
BORDER = 0


def color_to_bucas(c):
    return chr(ord('a') + int(c)) if 0 <= int(c) <= 22 else 'a'


def main():
    p = loader.load()
    pieces = p["pieces"]  # [256, 4], rows = top, right, bot, left
    board = json.load(open(ROOT / "output" / "v12_run" / "run_e2_5min_board.json"))
    W = H = 16
    placement = board["placement"]
    edges = []
    for pos in range(W * H):
        slot = placement[pos]
        if slot is None:
            edges.append("aaaa")
            continue
        pid = slot["piece_id"]
        rot = slot["rotation"]
        rotated = np.roll(pieces[pid], rot)
        edges.append("".join(color_to_bucas(c) for c in rotated))
    encoded = "".join(edges)
    url = f"https://e2.bucas.name/#puzzle=vol12_5min&board_w={W}&board_h={H}&board_edges={encoded}"
    print(url)
    # Also append to the run log so it's all in one place.
    log_path = ROOT / "output" / "v12_run" / "run_e2_5min.log"
    with log_path.open("a") as f:
        f.write(f"\n=== bucas URL ===\n{url}\n")


if __name__ == "__main__":
    main()
