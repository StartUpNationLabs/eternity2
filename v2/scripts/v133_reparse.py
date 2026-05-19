#!/usr/bin/env python3
"""V133-T2 — Re-parse saturation logs with a tighter regex.

The original parser grabbed `invocations=15234518` etc. as scores.
Use only the canonical "best: N/T" line from alns_e2's report.
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter

REPO = Path(__file__).resolve().parents[1]


def measure_density(size, pieces):
    P, R = len(pieces), 4
    n_int = (size - 1) * size + size * (size - 1)
    cf = Counter()
    for p in pieces:
        for r in range(R):
            n, e, s, w = p
            rot = [(n,e,s,w),(e,s,w,n),(s,w,n,e),(w,n,e,s)][r]
            for c in rot:
                cf[c] += 1
    total = P * R * 4
    p_match = sum((v/total)**2 for c, v in cf.items() if c != 0)
    return p_match, n_int


def load_csv(p):
    BORDER_RAW = 65535
    pieces = []
    with open(p) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            sides = [int(s.strip(), 2) for s in parts[:4]]
            sides = [0 if v == BORDER_RAW else v for v in sides]
            pieces.append(tuple(sides))
    return size, pieces


def parse_best_from_log(log_path):
    """Find the line 'best:    N/T (PCT%)' from alns_e2 report."""
    with open(log_path) as f:
        content = f.read()
    m = re.search(r"best:\s*(\d+)/(\d+)\s*\(([\d.]+)%\)", content)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def main():
    base = REPO / "output/vol-133/saturation_20260519T132959"
    rows = []

    CONFIGS = [
        (4, 2, "high_4x4_c2"),
        (5, 3, "high_5x5_c3"),
        (6, 3, "high_6x6_c3"),
        (8, 4, "med_8x8_c4"),
        (10, 5, "med_10x10_c5"),
        (12, 6, "med_12x12_c6"),
        (8, 16, "low_8x8_c16"),
        (10, 20, "low_10x10_c20"),
        (12, 24, "low_12x12_c24"),
    ]

    print(f"{'config':>16} {'seed':>4} {'p_match':>8} {'random%':>8} {'best':>5}/{'tgt':>3} {'pct':>6} {'gap':>6}", flush=True)
    for size, n_colors, label in CONFIGS:
        for seed in [42, 1, 7]:
            csv = base / f"{label}_seed{seed}.csv"
            log = base / f"{label}_seed{seed}_seed{seed}.log"
            if not csv.exists() or not log.exists():
                continue
            sz, pieces = load_csv(csv)
            pm, n_int = measure_density(sz, pieces)
            best, target = parse_best_from_log(log)
            if best is None: continue
            pct = best/target*100
            gap = pct - pm*100
            print(f"{label:>16} {seed:>4} {pm:>8.4f} {pm*100:>7.1f}% {best:>5}/{target:>3} "
                  f"{pct:>5.1f}% {gap:>+5.1f}", flush=True)
            rows.append({"label": label, "seed": seed, "p_match": pm,
                         "random_pct": pm*100, "best": best, "target": target,
                         "pct": pct, "gap": gap})

    # Median per config.
    print(f"\n{'config':>16} {'p_match':>8} {'random%':>8} {'med_pct':>8} {'med_gap':>8}", flush=True)
    by_label = {}
    for r in rows:
        by_label.setdefault(r['label'], []).append(r)
    for label, rs in by_label.items():
        pms = [r['p_match'] for r in rs]
        pcts = [r['pct'] for r in rs]
        gaps = [r['gap'] for r in rs]
        med_pm = sorted(pms)[len(pms)//2]
        med_pct = sorted(pcts)[len(pcts)//2]
        med_gap = sorted(gaps)[len(gaps)//2]
        print(f"{label:>16} {med_pm:>8.4f} {med_pm*100:>7.1f}% {med_pct:>7.1f}% {med_gap:>+7.1f}", flush=True)

    out = REPO / "output/vol-133/reparse.json"
    with open(out, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nWrote {out}", flush=True)


if __name__ == "__main__":
    main()
