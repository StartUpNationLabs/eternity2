#!/usr/bin/env python3
"""V178 STIGMA — Build initial pheromone matrix from corpus boards.

Pheromone matrix τ[p1, p2, d] = accumulated weight for piece p1 having
piece p2 as its `d`-neighbor (d ∈ {0=N, 1=E, 2=S, 3=W}).

Bootstrap from the 1278-board corpus. Each board contributes its
piece-piece adjacencies weighted by exp(γ · score / 480), so a 460
board contributes 4.5× more than a 440 board for γ=10.

Output JSON: {"shape": [256, 256, 4], "data": <flat list>, "score_pow_gamma": γ}

This pheromone serves as ranking SIGNAL for V155/V175 beam search,
or as INITIAL state for live pheromone updating during runs.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

N = 16
N_PIECES = 256


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


def update_pheromone(tau, placement, weight, size=N):
    """For each placed pair (pos, pos+1) east-adjacency and (pos, pos+N)
    south-adjacency, add `weight` to tau[p1, p2, dir]. Also record the
    reverse (W and N).
    """
    for y in range(size):
        for x in range(size):
            pos = y * size + x
            if placement[pos] is None: continue
            p1, _ = placement[pos]
            # East neighbor
            if x + 1 < size:
                rent = placement[pos + 1]
                if rent is not None:
                    p2, _ = rent
                    tau[p1][p2][1] += weight  # p1's east is p2
                    tau[p2][p1][3] += weight  # p2's west is p1
            # South neighbor
            if y + 1 < size:
                sent = placement[pos + size]
                if sent is not None:
                    p2, _ = sent
                    tau[p1][p2][2] += weight  # p1's south is p2
                    tau[p2][p1][0] += weight  # p2's north is p1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db-dir', default='database-400-480')
    ap.add_argument('--out', default='output/vol-178/pheromone_init.json')
    ap.add_argument('--gamma', type=float, default=10.0,
                    help='Weight = exp(gamma * score / 480). Higher = sharper bias toward high-score boards.')
    ap.add_argument('--min-score', type=int, default=440,
                    help='Skip boards below this score.')
    args = ap.parse_args()

    tau = [[[0.0] * 4 for _ in range(N_PIECES)] for _ in range(N_PIECES)]

    db = Path(REPO / args.db_dir)
    boards = sorted(db.glob('*.json'))
    print(f"Scanning {len(boards)} boards (min_score={args.min_score})")
    n_used = 0
    n_high = 0
    for bp in boards:
        try:
            score, pl = load_board(bp)
        except Exception:
            continue
        if score is None or score < args.min_score: continue
        # Higher-score boards weighted exponentially more.
        weight = math.exp(args.gamma * score / 480)
        update_pheromone(tau, pl, weight)
        n_used += 1
        if score >= 460: n_high += 1

    print(f"  used {n_used} boards ({n_high} ≥460)")

    # Stats
    total_weight = sum(tau[p1][p2][d] for p1 in range(N_PIECES) for p2 in range(N_PIECES) for d in range(4))
    nonzero = sum(1 for p1 in range(N_PIECES) for p2 in range(N_PIECES) for d in range(4)
                  if tau[p1][p2][d] > 0)
    print(f"  total weight: {total_weight:.1e}")
    print(f"  nonzero entries: {nonzero} / {N_PIECES * N_PIECES * 4} ({100 * nonzero / (N_PIECES**2 * 4):.1f}%)")

    # Top pairs (by max over directions)
    pair_max = []
    for p1 in range(N_PIECES):
        for p2 in range(N_PIECES):
            m = max(tau[p1][p2])
            if m > 0:
                pair_max.append((m, p1, p2))
    pair_max.sort(reverse=True)
    print(f"  top-10 highest-pheromone pairs:")
    for w, p1, p2 in pair_max[:10]:
        # which direction
        d = max(range(4), key=lambda x: tau[p1][p2][x])
        dirn = ['N', 'E', 'S', 'W'][d]
        print(f"    p{p1}→p{p2} ({dirn}): w={w:.1e}")

    # Save flat for Rust.
    flat = []
    for p1 in range(N_PIECES):
        for p2 in range(N_PIECES):
            for d in range(4):
                flat.append(tau[p1][p2][d])

    out_path = Path(REPO / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        'shape': [N_PIECES, N_PIECES, 4],
        'data': flat,
        'gamma': args.gamma,
        'min_score': args.min_score,
        'n_boards': n_used,
        'n_high_boards': n_high,
    }))
    print(f"  saved to {out_path}")


if __name__ == '__main__':
    main()
