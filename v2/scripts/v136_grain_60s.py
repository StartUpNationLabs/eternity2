#!/usr/bin/env python3
"""V136-T1 — GRAIN 60s budget (matched against ALNS 60s)."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from v135_grain_poc import load_csv, grow_grain, score_board_grain, total_interior_edges

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--n-crystals", type=int, default=8)
    ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    target = total_interior_edges(size)
    print(f"Puzzle: size={size}×{size} target={target}", flush=True)
    print(f"Budget: {args.seconds}s  K={args.n_crystals}", flush=True)
    best_score = -1
    best_seed = -1
    best_t = 0
    trials = 0
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        trials += 1
        seed = trials * 7 + 17
        board, _ = grow_grain(size, pieces, args.n_crystals, seed)
        score = score_board_grain(board, size)
        if score > best_score:
            best_score = score
            best_seed = seed
            best_t = time.time() - t0
            print(f"  trial {trials}: t={time.time()-t0:.1f}s NEW BEST seed={seed} "
                  f"score={score}/{target} ({score/target*100:.1f}%)", flush=True)
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s. Total trials: {trials}", flush=True)
    print(f"Best: {best_score}/{target} ({best_score/target*100:.1f}%) at seed={best_seed} t={best_t:.1f}s", flush=True)
    print(f"Trials/s: {trials/elapsed:.1f}", flush=True)

if __name__ == "__main__":
    main()
