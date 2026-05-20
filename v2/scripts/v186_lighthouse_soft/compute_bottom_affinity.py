#!/usr/bin/env python3
"""Compute β(p) = bottom-row affinity for each piece from the corpus prior.

Output: JSON list of 256 floats, where β[p] is the fraction of corpus
boards where piece p was placed in rows 12–15.
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prior', default='scripts/v155_prior/prior_matrix_high459.json')
    ap.add_argument('--out', default='scripts/v186_lighthouse_soft/bottom_affinity.json')
    ap.add_argument('--bottom-rows', nargs='+', type=int, default=[12, 13, 14, 15])
    ap.add_argument('--top-rows', nargs='+', type=int, default=[0, 1, 2, 3])
    args = ap.parse_args()

    prior = json.load(open(args.prior))
    M = prior['matrix']
    n_pieces = prior['n_pieces']
    n_positions = prior['n_positions']
    n_boards = prior['n_boards']

    bottom_positions = []
    for r in args.bottom_rows:
        for c in range(16):
            bottom_positions.append(r * 16 + c)
    top_positions = []
    for r in args.top_rows:
        for c in range(16):
            top_positions.append(r * 16 + c)

    beta = []
    tau = []
    for p in range(n_pieces):
        b = sum(M[p][pos] for pos in bottom_positions) / n_boards
        t = sum(M[p][pos] for pos in top_positions) / n_boards
        beta.append(b)
        tau.append(t)

    payload = {
        'n_pieces': n_pieces,
        'n_boards': n_boards,
        'bottom_rows': args.bottom_rows,
        'top_rows': args.top_rows,
        'beta_bottom': beta,
        'tau_top': tau,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(payload))
    print(f"wrote {args.out}")
    print(f"  β bottom: max={max(beta):.3f}, top-10 pids: "
          f"{sorted(range(n_pieces), key=lambda p: -beta[p])[:10]}")
    print(f"  τ top:    max={max(tau):.3f}, top-10 pids: "
          f"{sorted(range(n_pieces), key=lambda p: -tau[p])[:10]}")
    high_beta = sum(1 for b in beta if b > 0.5)
    high_tau = sum(1 for t in tau if t > 0.5)
    print(f"  pieces with β > 0.5: {high_beta}, τ > 0.5: {high_tau}")


if __name__ == '__main__':
    main()
