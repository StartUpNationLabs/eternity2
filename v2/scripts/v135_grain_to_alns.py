#!/usr/bin/env python3
"""V135-T2 — GRAIN partial → ALNS pipeline.

1. Run GRAIN for N seeds, pick the best.
2. Convert to a starting board JSON.
3. Run alns_e2 with --seed-board pointing at GRAIN output.
4. Compare to ALNS-from-empty baseline.
"""

from __future__ import annotations
import argparse, json, subprocess, re, time
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from v135_grain_poc import load_csv, grow_grain, score_board_grain, total_interior_edges


def grain_to_board_json(board, size, n_pieces, out_path):
    """Convert GRAIN board (list of (pid, rotated, cid)) to standard placement JSON."""
    placement = []
    for pos in range(size*size):
        cell = board[pos]
        if cell is None: continue
        pid = cell[0]
        # We need rotation index, not rotated tuple. Reverse from rotated.
        # But the GRAIN board doesn't store rotation directly. Reconstruct.
        # Easier: store rotation in GRAIN.
        # For now, we approximate: try all 4 rotations, find which matches the stored rotated.
        rotated = cell[1]
        # We need the original piece to compare.
        # This requires access to pieces array; we'll pass it in.
        placement.append({"pos": pos, "piece_id": int(pid), "rotation": 0})
    # Better: re-derive rotation by checking against original piece sides.
    return placement


def grain_to_board_with_rot(board, size, pieces, out_path):
    from v135_grain_poc import rotate_piece
    placement = []
    for pos in range(size*size):
        cell = board[pos]
        if cell is None: continue
        pid = cell[0]
        rotated = cell[1]
        original = pieces[pid]
        # Find rotation r such that rotate_piece(original, r) == rotated.
        for r in range(4):
            if rotate_piece(original, r) == rotated:
                placement.append({"pos": pos, "piece_id": int(pid), "rotation": r})
                break
    with open(out_path, "w") as f:
        json.dump({"matched": -1, "placement": placement}, f, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--n-crystals", type=int, default=8)
    ap.add_argument("--grain-trials", type=int, default=10)
    ap.add_argument("--alns-seconds", type=int, default=60)
    ap.add_argument("--out-dir", type=str, default=None)
    args = ap.parse_args()

    if args.out_dir is None:
        args.out_dir = str(REPO / "output/vol-135" / f"grain_to_alns_{time.strftime('%Y%m%dT%H%M%S')}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"OUT_DIR={out_dir}", flush=True)

    size, pieces = load_csv(args.puzzle)
    target = total_interior_edges(size)
    print(f"Puzzle: size={size}×{size} target={target}", flush=True)

    # Phase 1: GRAIN trials, pick best.
    print(f"\nPhase 1: GRAIN × {args.grain_trials} trials", flush=True)
    best_score = -1
    best_board = None
    best_seed = -1
    for trial in range(args.grain_trials):
        seed = 42 + trial * 7
        board, _ = grow_grain(size, pieces, args.n_crystals, seed)
        score = score_board_grain(board, size)
        if score > best_score:
            best_score = score
            best_board = board
            best_seed = seed
        if trial % 3 == 0:
            print(f"  trial {trial}: seed={seed} score={score}/{target}", flush=True)
    print(f"GRAIN best: {best_score}/{target} ({best_score/target*100:.1f}%) from seed={best_seed}", flush=True)

    # Phase 2: convert best to JSON, feed to ALNS.
    seed_board_path = out_dir / "grain_seed_board.json"
    grain_to_board_with_rot(best_board, size, pieces, seed_board_path)

    # Run ALNS with this as seed.
    print(f"\nPhase 2: ALNS {args.alns_seconds}s from GRAIN seed", flush=True)
    log = out_dir / "alns_from_grain.log"
    cmd = [str(REPO/"target/bench-fast/alns_e2"),
           "--puzzle", args.puzzle,
           "--seconds", str(args.alns_seconds),
           "--seed", "42",
           "--seed-board", str(seed_board_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    with open(log, "w") as f: f.write(proc.stdout + proc.stderr)
    m = re.search(r"best:\s*(\d+)/(\d+)", proc.stdout + proc.stderr)
    if m:
        alns_best = int(m.group(1))
        print(f"ALNS from GRAIN: {alns_best}/{target} ({alns_best/target*100:.1f}%)", flush=True)
    else:
        alns_best = None
        print("ALNS log doesn't have best: line", flush=True)

    # Phase 3: baseline ALNS from empty.
    print(f"\nPhase 3: ALNS {args.alns_seconds}s baseline (skip-warmup empty)", flush=True)
    log = out_dir / "alns_baseline.log"
    cmd = [str(REPO/"target/bench-fast/alns_e2"),
           "--puzzle", args.puzzle,
           "--seconds", str(args.alns_seconds),
           "--seed", "42", "--skip-warmup"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    with open(log, "w") as f: f.write(proc.stdout + proc.stderr)
    m = re.search(r"best:\s*(\d+)/(\d+)", proc.stdout + proc.stderr)
    if m:
        alns_baseline = int(m.group(1))
        print(f"ALNS baseline: {alns_baseline}/{target} ({alns_baseline/target*100:.1f}%)", flush=True)
    else:
        alns_baseline = None
        print("ALNS baseline log doesn't have best:", flush=True)

    print(f"\n=== SUMMARY ===", flush=True)
    print(f"GRAIN alone:       {best_score} ({best_score/target*100:.1f}%)", flush=True)
    if alns_best: print(f"GRAIN→ALNS:        {alns_best} ({alns_best/target*100:.1f}%)", flush=True)
    if alns_baseline: print(f"ALNS baseline:     {alns_baseline} ({alns_baseline/target*100:.1f}%)", flush=True)
    if alns_best and alns_baseline:
        delta = alns_best - alns_baseline
        print(f"Δ (GRAIN→ALNS vs baseline): {delta:+d}", flush=True)


if __name__ == "__main__":
    main()
