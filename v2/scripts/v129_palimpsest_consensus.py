#!/usr/bin/env python3
"""V129-T1 — PALIMPSEST: historical-consensus invariant mining.

For each adjacent cell-pair (i, j, direction), compute the per-realized-
pair-tuple score-weighted persistence:

  persistence(pair) = sum_{board with pair} (score) / N_boards_with_pair

But the more useful metric is BASIN-SEPARATED:
  - persistence_high(pair) = freq in score ≥ 460
  - persistence_total(pair) = freq in all boards
  - score_ceiling(pair) = max score of a board CONTAINING this pair

Two interesting categories:

  A. HIGH-PERSISTENCE-HIGH-CEILING pairs: appear in many boards AND
     in a 462+ board. These are "good consensus" — likely correct.

  B. HIGH-PERSISTENCE-LOW-CEILING pairs: appear in many ≤461 boards
     but NEVER in 462+ boards. These are the CONSENSUS TRAPS the
     brainstorm warned about — the agreed-upon wrong choice that
     locks the search into our 461 family.

Output: lists of A and B candidates; destroy-target list for ALNS.
"""

from __future__ import annotations
import json
import sys
import time
from pathlib import Path
from collections import defaultdict, Counter

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "database-400-480"
OUT_DIR = REPO / "output/vol-129" / f"palimpsest_{time.strftime('%Y%m%dT%H%M%S')}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W = 16
N_CELLS = 256


def adjacent_pairs():
    for r in range(W):
        for c in range(W):
            i = r * W + c
            if c < W - 1:
                yield (i, i + 1, 'E')
            if r < W - 1:
                yield (i, i + W, 'S')


def load_record(path):
    try:
        d = json.load(open(path))
    except Exception: return None
    matched = d.get("matched")
    pl = d.get("placement", [])
    if not isinstance(matched, int) or not isinstance(pl, list): return None
    placement = {}
    for idx, p in enumerate(pl):
        if not isinstance(p, dict): continue
        pos = p.get("pos", idx)
        if "piece_id" in p and "rotation" in p:
            placement[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    if len(placement) != N_CELLS: return None
    return matched, placement


def main():
    print(f"OUT_DIR={OUT_DIR}", flush=True)
    records = []
    for path in sorted(DB.glob("*.json")):
        r = load_record(path)
        if r: records.append(r)
    print(f"Loaded {len(records)} records.", flush=True)

    pair_geom = list(adjacent_pairs())
    n_adj = len(pair_geom)

    # For each pair-tuple (i, j, d, pi, ri, pj, rj):
    #   count_per_score_bucket[bucket] += 1 for each occurrence
    #   max_score → highest score of any board containing this pair-tuple
    #   total_count
    pair_max_score = {}    # tuple → max score
    pair_count = defaultdict(int)  # tuple → total occurrences
    pair_count_low = defaultdict(int)  # tuple → count in score < 460
    pair_count_high = defaultdict(int)  # tuple → count in score ≥ 462

    SCORE_HIGH = 462   # what we want to BREAK to
    SCORE_LOW = 460    # the basins we want to escape

    for matched, placement in records:
        for (i, j, d) in pair_geom:
            pi, ri = placement[i]
            pj, rj = placement[j]
            key = (i, j, d, pi, ri, pj, rj)
            pair_count[key] += 1
            if matched < SCORE_LOW:
                pair_count_low[key] += 1
            elif matched >= SCORE_HIGH:
                pair_count_high[key] += 1
            if key not in pair_max_score or matched > pair_max_score[key]:
                pair_max_score[key] = matched

    print(f"Total distinct pair-tuples: {len(pair_count)}", flush=True)

    # Consensus categories:
    # A: HIGH-PERSISTENCE-HIGH-CEILING: count ≥ 5 AND max_score ≥ 462
    # B: HIGH-PERSISTENCE-LOW-CEILING (TRAP): count ≥ 20 AND max_score ≤ 460
    cat_A = []  # likely-correct consensus
    cat_B = []  # CONSENSUS TRAPS

    for key, cnt in pair_count.items():
        max_s = pair_max_score[key]
        if cnt >= 5 and max_s >= SCORE_HIGH:
            cat_A.append((key, cnt, max_s))
        if cnt >= 20 and max_s <= 460:
            cat_B.append((key, cnt, max_s))

    cat_A.sort(key=lambda x: (-x[2], -x[1]))
    cat_B.sort(key=lambda x: (-x[1], -x[2]))

    print(f"\nCategory A (likely-correct, count≥5, max≥{SCORE_HIGH}): {len(cat_A)}", flush=True)
    print(f"Top 10:", flush=True)
    print(f"{'i':>4} {'j':>4} {'d':>2} {'pi':>4} {'ri':>3} {'pj':>4} {'rj':>3} {'cnt':>4} {'max':>4}", flush=True)
    for key, cnt, mx in cat_A[:10]:
        i, j, d, pi, ri, pj, rj = key
        print(f"{i:>4} {j:>4} {d:>2} {pi:>4} {ri:>3} {pj:>4} {rj:>3} {cnt:>4} {mx:>4}", flush=True)

    print(f"\nCategory B (CONSENSUS TRAPS, count≥20, max≤460): {len(cat_B)}", flush=True)
    print(f"Top 20:", flush=True)
    print(f"{'i':>4} {'j':>4} {'d':>2} {'pi':>4} {'ri':>3} {'pj':>4} {'rj':>3} {'cnt':>4} {'max':>4}", flush=True)
    for key, cnt, mx in cat_B[:20]:
        i, j, d, pi, ri, pj, rj = key
        print(f"{i:>4} {j:>4} {d:>2} {pi:>4} {ri:>3} {pj:>4} {rj:>3} {cnt:>4} {mx:>4}", flush=True)

    # Build a "destroy-target" position set: positions involved in any cat-B pair.
    trap_positions = set()
    for key, _, _ in cat_B:
        trap_positions.add(key[0])
        trap_positions.add(key[1])
    print(f"\nDistinct positions in any consensus trap: {len(trap_positions)}", flush=True)

    out = {
        "n_records": len(records),
        "score_high_threshold": SCORE_HIGH,
        "score_low_threshold": SCORE_LOW,
        "n_pair_tuples": len(pair_count),
        "cat_A_likely_correct": [
            {"key": list(k), "count": c, "max_score": m}
            for k, c, m in cat_A[:500]
        ],
        "cat_B_consensus_traps": [
            {"key": list(k), "count": c, "max_score": m}
            for k, c, m in cat_B[:500]
        ],
        "trap_positions": sorted(trap_positions),
    }
    out_path = OUT_DIR / "consensus.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
