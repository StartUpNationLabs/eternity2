#!/usr/bin/env python3
"""V181 KEYRING — build a patch-level prior matrix.

For each 2x2 patch (4 pieces with rotations), compute a log-odds ratio:

  patch_score(p) = log(count_high(p) + α) - log(count_low(p) + α)

where high = ≥460, low = <460, α = 0.5 (Laplace smoothing).

Save to JSON with patch as 8-int tuple key (encoded as packed u64 since
each piece_id ≤ 256 = 8 bits, rotation 2 bits; 4 cells × 10 bits = 40 bits
fits in u64).

Output format:
  {
    "n_high_boards": 23,
    "n_low_boards": 1255,
    "alpha": 0.5,
    "patches": {
      "<u64_key>": {"count_high": N, "count_low": M, "score": float}
    }
  }
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from collections import Counter

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


def patch_key(tl, tr, bl, br):
    """Encode 4 (pid, rot) as a single u64: 10 bits per cell × 4 cells."""
    def enc(pr):
        pid, rot = pr
        return (pid << 2) | rot  # 8+2 = 10 bits
    return (enc(tl) << 30) | (enc(tr) << 20) | (enc(bl) << 10) | enc(br)


def patches_in(placement, size=16):
    out = []
    for y in range(size - 1):
        for x in range(size - 1):
            tl = placement[y * size + x]
            tr = placement[y * size + x + 1]
            bl = placement[(y + 1) * size + x]
            br = placement[(y + 1) * size + x + 1]
            if tl and tr and bl and br:
                out.append(patch_key(tl, tr, bl, br))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db-dir', default='database-400-480')
    ap.add_argument('--out', default='output/vol-181/patch_prior.json')
    ap.add_argument('--alpha', type=float, default=0.5)
    ap.add_argument('--high-threshold', type=int, default=460)
    args = ap.parse_args()

    db = Path(REPO / args.db_dir)
    boards = sorted(db.glob('*.json'))
    print(f"Loading {len(boards)} boards")

    high = Counter()
    low = Counter()
    n_high = 0
    n_low = 0
    for bp in boards:
        try:
            score, pl = load_board(bp)
        except Exception:
            continue
        if score is None: continue
        if not all(p is not None for p in pl): continue
        patches = patches_in(pl)
        if score >= args.high_threshold:
            for p in patches:
                high[p] += 1
            n_high += 1
        else:
            for p in patches:
                low[p] += 1
            n_low += 1

    print(f"n_high={n_high}, n_low={n_low}")
    all_patches = set(high) | set(low)
    print(f"unique patches: {len(all_patches)}")

    # Build score table — use categorical scoring (more robust to imbalance):
    #   in high only:    score = +1.0
    #   in both:         score = 0.0
    #   in low only:     score = -0.2 (mild penalty; most low patches are noise)
    #   never observed:  not in table (no contribution)
    log_ratio = {}
    for p in all_patches:
        h = high.get(p, 0)
        l = low.get(p, 0)
        if h > 0 and l == 0:
            score = 1.0
        elif h > 0 and l > 0:
            score = 0.0
        else:  # h == 0, l > 0
            score = -0.2
        log_ratio[str(p)] = {'h': h, 'l': l, 's': score}

    print(f"score distribution (log-ratio):")
    scores = sorted([v['s'] for v in log_ratio.values()])
    n = len(scores)
    print(f"  min={scores[0]:.2f}  p25={scores[n//4]:.2f}  med={scores[n//2]:.2f}  p75={scores[3*n//4]:.2f}  max={scores[-1]:.2f}")
    # How many positive (high-favored)?
    n_pos = sum(1 for s in scores if s > 0)
    print(f"  patches with positive score (high-favored): {n_pos}")

    out_path = Path(REPO / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        'n_high_boards': n_high,
        'n_low_boards': n_low,
        'alpha': args.alpha,
        'scoring': 'categorical (high_only=+1, both=0, low_only=-0.2)',
        'high_threshold': args.high_threshold,
        'patches': log_ratio,
    }))
    print(f"saved {len(log_ratio)} patch scores to {out_path}")


if __name__ == '__main__':
    main()
