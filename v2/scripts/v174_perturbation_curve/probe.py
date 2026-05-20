#!/usr/bin/env python3
"""V174 PERTURBATION CURVE — measure how far we can move from corpus
before score collapses.

Take V155-direct 460 board (5 s=0 cells, basically corpus-locked).
For K in {10, 20, 30, 50, 75, 100, 130, 160, 200, 256}:
  - Randomly swap K pieces with each other (preserving piece-id uniqueness).
  - Run 5min ALNS to recover.
  - Record: pre-ALNS score, post-ALNS score, post-ALNS s=0 cells.

This probes the basin geometry:
  - Small K: ALNS fully recovers to 460 (we never left).
  - Medium K: some seeds recover, some don't. Multiple basins visited.
  - Large K: random board, ALNS struggles, scores 440-450.

The interesting regime: medium K where ALNS lifts to >460 (basin transit).

Output: K-vs-score curve + basin (corner_perm) of recovered boards.
"""
from __future__ import annotations
import argparse
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_board(path, size=16):
    d = json.loads(Path(path).read_text())
    pl = d.get('placement', [])
    placement = [None] * (size * size)
    has_pos = any(isinstance(e, dict) and 'pos' in e for e in pl if e is not None)
    for i, entry in enumerate(pl):
        if entry is None: continue
        pos = int(entry['pos']) if has_pos else i
        placement[pos] = (int(entry['piece_id']), int(entry['rotation']))
    return d.get('matched'), placement


def write_board(path, placement, score=0):
    out = []
    for pos, ent in enumerate(placement):
        if ent is None:
            out.append(None)
        else:
            pid, rot = ent
            out.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    d = {'placement': out, 'matched': score}
    Path(path).write_text(json.dumps(d))


def perturb_k_swaps(placement, k, seed, hint_positions=None):
    """Randomly select 2K cells (excluding pinned), pair them, swap pieces."""
    rng = random.Random(seed)
    hint_positions = hint_positions or set()
    candidates = [pos for pos, ent in enumerate(placement)
                  if ent is not None and pos not in hint_positions]
    rng.shuffle(candidates)
    new = list(placement)
    for i in range(min(k, len(candidates) // 2)):
        a = candidates[2 * i]
        b = candidates[2 * i + 1]
        new[a], new[b] = new[b], new[a]
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='Source 460 board (V155-direct preferred)')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--k-values', nargs='+', type=int,
                    default=[10, 20, 30, 50, 75, 100, 130, 160])
    ap.add_argument('--seeds-per-k', type=int, default=3)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_score, base = load_board(args.base)
    print(f"Base: {args.base} score={base_score}")

    # Canonical hint positions on 16×16 E2 are 135, 210, 34, 221, 45.
    hints = {135, 210, 34, 221, 45}

    for k in args.k_values:
        for seed in range(1, args.seeds_per_k + 1):
            perturbed = perturb_k_swaps(base, k, seed, hint_positions=hints)
            out_path = out_dir / f'k{k:03d}_s{seed}.json'
            write_board(out_path, perturbed)
            print(f"  k={k:>3} seed={seed} -> {out_path.name}")


if __name__ == '__main__':
    main()
