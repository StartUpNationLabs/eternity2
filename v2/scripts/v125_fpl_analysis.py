#!/usr/bin/env python3
"""V125-T34 — Frozen-Pair Lifting (FPL) analysis.

Hypothesis: in any 462+ board (and especially the unique 480), certain
adjacent piece-pairs at specific (pos_a, pos_b, rot_a, rot_b) tuples
appear with positive log-odds across high-score samples and negative
log-odds across low-score samples. These are *candidate invariants*.

If we pin a candidate-invariant pair as additional hints, the search
restricts to boards CONSISTENT with that pair. If the true 480 contains
the pair, restriction does not lose the solution; if it doesn't,
restriction may force ALNS into a different basin → possibly +1 over 461.

This script:
1. Loads every board in database-400-480/.
2. Buckets by score: HIGH (≥ 459), MID (445-458), LOW (400-444).
3. For each adjacent (i,j), enumerates the realized
   (piece_a, rot_a, piece_b, rot_b) tuple. Counts occurrences in each bucket.
4. Computes log-odds = log( (count_HIGH + α) / (count_LOW + α) ) - log( (N_HIGH / N_LOW) ).
   Pairs with log-odds >> 0 are HIGH-enriched (candidate invariants).
5. Outputs top 100 candidates → JSON.

Output: output/vol-125/fpl_candidates_<timestamp>.json
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "database-400-480"
OUT_DIR = REPO / "output" / "vol-125" / f"fpl_{time.strftime('%Y%m%dT%H%M%S')}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W = 16
N_CELLS = 256

HIGH_THRESHOLD = 459  # ≥459 = HIGH (includes 459/460/461)
MID_LOW = 445         # 445-458 = MID
LOW_HIGH = 444        # 400-444 = LOW

ALPHA = 1.0  # Laplace smoothing


def adjacent_pairs():
    """Yield (i, j, direction) for every ordered adjacent pair i→j.

    direction: 'E' (i is west of j), 'S' (i is north of j).
    Yields each pair twice (once per direction).
    """
    for r in range(W):
        for c in range(W):
            i = r * W + c
            if c < W - 1:
                yield (i, i + 1, 'E')
            if r < W - 1:
                yield (i, i + W, 'S')


def load_record(path: Path):
    """Return (matched, {pos: (pid, rot)}) or None."""
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        return None
    matched = d.get("matched")
    pl = d.get("placement", [])
    if not isinstance(matched, int) or not isinstance(pl, list):
        return None
    placement = {}
    for idx, p in enumerate(pl):
        if not isinstance(p, dict):
            continue
        pos = p.get("pos", idx)
        if "piece_id" in p and "rotation" in p:
            placement[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    if len(placement) != N_CELLS:
        return None
    return matched, placement


def main():
    print(f"OUT_DIR={OUT_DIR}", flush=True)
    records = []
    for path in sorted(DB.glob("*.json")):
        r = load_record(path)
        if r is None:
            continue
        records.append(r)

    n_high = sum(1 for m, _ in records if m >= HIGH_THRESHOLD)
    n_mid = sum(1 for m, _ in records if MID_LOW <= m < HIGH_THRESHOLD)
    n_low = sum(1 for m, _ in records if m <= LOW_HIGH)
    print(f"Loaded {len(records)} records: HIGH(≥{HIGH_THRESHOLD})={n_high}, "
          f"MID({MID_LOW}-{HIGH_THRESHOLD-1})={n_mid}, "
          f"LOW(≤{LOW_HIGH})={n_low}", flush=True)

    if n_high == 0:
        print("ERROR: no HIGH boards — adjust threshold.", flush=True)
        sys.exit(1)

    # For each adjacent (i,j,dir), tally tuples (pid_i, rot_i, pid_j, rot_j) per bucket.
    # Key: (i, j, dir, pid_i, rot_i, pid_j, rot_j)
    high_counts: dict[tuple, int] = defaultdict(int)
    low_counts: dict[tuple, int] = defaultdict(int)
    mid_counts: dict[tuple, int] = defaultdict(int)

    pair_geometry = list(adjacent_pairs())

    for matched, placement in records:
        if matched >= HIGH_THRESHOLD:
            bucket = high_counts
        elif matched <= LOW_HIGH:
            bucket = low_counts
        else:
            bucket = mid_counts
        for (i, j, d) in pair_geometry:
            if i not in placement or j not in placement:
                continue
            pi, ri = placement[i]
            pj, rj = placement[j]
            key = (i, j, d, pi, ri, pj, rj)
            bucket[key] += 1

    # Log-odds.
    candidates = []
    all_keys = set(high_counts.keys()) | set(low_counts.keys()) | set(mid_counts.keys())
    print(f"Distinct realized pair-tuples: {len(all_keys)}", flush=True)

    for key in all_keys:
        h = high_counts.get(key, 0)
        l = low_counts.get(key, 0)
        m = mid_counts.get(key, 0)
        # Require at least 2 HIGH occurrences (otherwise pair is incidental).
        if h < 2:
            continue
        # log-odds vs LOW
        p_high = (h + ALPHA) / (n_high + 2 * ALPHA)
        p_low = (l + ALPHA) / (n_low + 2 * ALPHA)
        log_odds_low = math.log(p_high / p_low)
        p_mid = (m + ALPHA) / (n_mid + 2 * ALPHA)
        log_odds_mid = math.log(p_high / p_mid)
        # Combined score: enriched in HIGH vs both LOW and MID.
        combined = log_odds_low + log_odds_mid
        candidates.append({
            "i": key[0], "j": key[1], "dir": key[2],
            "pi": key[3], "ri": key[4],
            "pj": key[5], "rj": key[6],
            "h": h, "m": m, "l": l,
            "lo_low": log_odds_low,
            "lo_mid": log_odds_mid,
            "combined": combined,
        })

    candidates.sort(key=lambda x: -x["combined"])
    top = candidates[:200]

    print(f"\nTop 30 candidate-invariant pairs:", flush=True)
    print(f"{'i':>4} {'j':>4} {'d':>2} {'pi':>4} {'ri':>3} {'pj':>4} {'rj':>3} "
          f"{'h':>3} {'m':>3} {'l':>3} {'lo_low':>7} {'lo_mid':>7} {'comb':>7}", flush=True)
    for c in top[:30]:
        print(f"{c['i']:>4} {c['j']:>4} {c['dir']:>2} "
              f"{c['pi']:>4} {c['ri']:>3} {c['pj']:>4} {c['rj']:>3} "
              f"{c['h']:>3} {c['m']:>3} {c['l']:>3} "
              f"{c['lo_low']:>7.2f} {c['lo_mid']:>7.2f} {c['combined']:>7.2f}",
              flush=True)

    out = {
        "n_records": len(records),
        "n_high": n_high,
        "n_mid": n_mid,
        "n_low": n_low,
        "high_threshold": HIGH_THRESHOLD,
        "n_distinct_pair_tuples": len(all_keys),
        "candidates": top,
    }
    out_path = OUT_DIR / "fpl_candidates.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)
    print(f"Total candidates with h≥2: {len(candidates)}", flush=True)


if __name__ == "__main__":
    main()
