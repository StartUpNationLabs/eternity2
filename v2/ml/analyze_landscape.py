"""Analyze landscape_explorer output.

Reads summary.jsonl + per-restart board JSONs, computes:
  - score histogram
  - pairwise Hamming distance matrix
  - clustering (within Hamming threshold)
  - per-score-class basin diversity
"""

from __future__ import annotations

import glob
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "output/vol-35/landscape_6x6_1000"

    summary_path = os.path.join(out_dir, "summary.jsonl")
    rows = []
    with open(summary_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    print(f"[load] {len(rows)} restarts from {out_dir}")

    scores = [r["score"] for r in rows]
    print(f"\n=== score histogram ===")
    hist = Counter(scores)
    for s in sorted(hist):
        print(f"  {s}: {hist[s]}")
    print(f"\nmean={sum(scores)/len(scores):.1f} max={max(scores)} min={min(scores)}")

    # Load each board's placement
    boards = []
    for r in rows:
        try:
            d = json.load(open(r["path"]))
            pl = d.get("placement", [])
            config = tuple(
                (p["piece_id"], p["rotation"]) if isinstance(p, dict) else None
                for p in pl
            )
            boards.append((r["restart_seed"], r["score"], config))
        except Exception:
            continue
    print(f"[load] {len(boards)} board configs")

    # Pairwise hamming on (piece_id, rotation) per position
    n = len(boards)
    if n > 500:
        print(f"[skip] n={n} too large for O(n^2) full matrix; sampling 500")
        boards = boards[:500]
        n = 500

    # For each pair, compute Hamming
    hamming_dist = []
    for i in range(n):
        ci = boards[i][2]
        for j in range(i + 1, n):
            cj = boards[j][2]
            h = sum(1 for k in range(len(ci)) if ci[k] != cj[k])
            hamming_dist.append((i, j, h, boards[i][1], boards[j][1]))

    # Hamming distribution
    h_only = [d[2] for d in hamming_dist]
    print(f"\n=== Hamming distance distribution (cells differing) ===")
    print(f"min={min(h_only)} max={max(h_only)} mean={sum(h_only)/len(h_only):.1f}")
    h_hist = Counter()
    for h in h_only:
        # Bucket into 5-wide bins
        b = (h // 5) * 5
        h_hist[b] += 1
    for b in sorted(h_hist):
        print(f"  H={b:>2}-{b + 4:>2}: {h_hist[b]}")

    # Cluster by hamming < threshold
    # Use a simple union-find with threshold sweep
    for threshold in [5, 10, 15, 20, 25]:
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, j, h, _, _ in hamming_dist:
            if h <= threshold:
                pi, pj = find(i), find(j)
                if pi != pj:
                    parent[pi] = pj
        clusters = Counter(find(i) for i in range(n))
        print(f"\n[cluster] threshold H≤{threshold}: {len(clusters)} clusters (out of {n} restarts)")
        big_clusters = [(c, s) for c, s in clusters.items() if s > 1]
        if big_clusters:
            sizes = sorted([s for _, s in big_clusters], reverse=True)
            print(f"  top cluster sizes: {sizes[:10]}")

    # Fitness-distance correlation: from each LO, distance to highest-scoring LO
    if boards:
        best_idx = max(range(n), key=lambda i: boards[i][1])
        best = boards[best_idx]
        print(f"\n=== FDC: distance to highest-score LO (score={best[1]}) ===")
        for i, (sid, score, config) in enumerate(boards):
            if i == best_idx:
                continue
            h = sum(1 for k in range(len(config)) if config[k] != best[2][k])
            # print(f"  seed={sid} score={score} H_to_best={h}")
            pass
        # Compute correlation
        try:
            import statistics
            xs = []
            ys = []
            for i, (_, score, config) in enumerate(boards):
                if i == best_idx:
                    continue
                h = sum(1 for k in range(len(config)) if config[k] != best[2][k])
                xs.append(h)
                ys.append(score)
            if len(xs) >= 2:
                mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
                num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
                den_x = (sum((x - mean_x) ** 2 for x in xs)) ** 0.5
                den_y = (sum((y - mean_y) ** 2 for y in ys)) ** 0.5
                if den_x > 0 and den_y > 0:
                    r = num / (den_x * den_y)
                    print(f"FDC Pearson r = {r:.3f}")
                    print(f"  (negative r → close to best = high score: classic 'big-valley')")
                    print(f"  (positive r → close to best = low score: rugged/random)")
        except Exception as e:
            print(f"FDC error: {e}")


if __name__ == "__main__":
    main()
