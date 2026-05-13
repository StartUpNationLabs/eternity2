"""T4 — Analyse LOT_TRACE stderr output.

Format of each line:
  LOT_TRACE depth=N pos=N dom=N tie_len=N top_key=N

We compute:
  - histogram of tie_len (how many candidates clustered within EPS)
  - per-depth fire-rate (lines per depth normalized)
  - per-depth NN-call rate (= tie_len >= 2 count / lines at that depth)
  - cumulative NN calls
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict


def parse_trace(path):
    rows = []
    with open(path) as f:
        for line in f:
            if not line.startswith("LOT_TRACE"):
                continue
            parts = dict(p.split("=") for p in line.split()[1:])
            rows.append({
                "depth": int(parts["depth"]),
                "pos": int(parts["pos"]),
                "dom": int(parts["dom"]),
                "tie_len": int(parts["tie_len"]),
                "top_key": int(parts["top_key"]),
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = parse_trace(args.trace)
    print(f"=== LOT_TRACE analysis: {args.trace} ===")
    print(f"total events: {len(rows)}")
    if not rows:
        print("(empty)")
        return

    tie_hist = Counter(r["tie_len"] for r in rows)
    dom_hist = Counter(r["dom"] for r in rows)
    nn_called = sum(1 for r in rows if r["tie_len"] >= 2)

    print(f"NN-call events (tie_len >= 2): {nn_called} ({100*nn_called/len(rows):.1f}%)")
    print(f"\ntie_len histogram (top 10):")
    for tl, c in sorted(tie_hist.items())[:15]:
        bar = "#" * min(60, int(60 * c / max(tie_hist.values())))
        print(f"  tie_len={tl:>3}: {c:>7}  {bar}")

    print(f"\ndom-size histogram (top 10):")
    for d, c in sorted(dom_hist.items())[:15]:
        bar = "#" * min(60, int(60 * c / max(dom_hist.values())))
        print(f"  dom={d:>3}: {c:>7}  {bar}")

    # Per-depth breakdown — bucket by 10
    by_depth_bucket = defaultdict(lambda: {"events": 0, "nn": 0})
    for r in rows:
        b = (r["depth"] // 10) * 10
        by_depth_bucket[b]["events"] += 1
        if r["tie_len"] >= 2:
            by_depth_bucket[b]["nn"] += 1

    print(f"\nPer-depth-bucket (10-bin) breakdown:")
    print(f"  {'depth':>6}  {'events':>8}  {'nn':>6}  {'nn_rate':>7}")
    for b in sorted(by_depth_bucket):
        d = by_depth_bucket[b]
        rate = d['nn'] / max(1, d['events'])
        print(f"  {b:>3}-{b+9:>3}  {d['events']:>8}  {d['nn']:>6}  {rate*100:>6.1f}%")


if __name__ == "__main__":
    main()
