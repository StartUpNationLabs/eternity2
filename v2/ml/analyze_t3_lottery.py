"""Vol-34 T3 — analyze the lottery summary.jsonl produced by run_t3_lottery.sh.

Reports:
  - score distribution (histogram)
  - per-partial mean / max / min
  - top-K boards
  - whether the basin-family ceilings are visible (multiple seeds → same score)
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def main():
    summary_path = sys.argv[1] if len(sys.argv) > 1 else "output/vol-34/t3_full/summary.jsonl"
    rows = []
    with open(summary_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    print(f"[load] {len(rows)} runs from {summary_path}")

    scores = [r["matched"] for r in rows]
    if not scores:
        print("(empty)")
        return

    print(f"\n=== overall ===")
    print(f"max={max(scores)} mean={sum(scores)/len(scores):.1f} min={min(scores)}")
    print(f"median={sorted(scores)[len(scores) // 2]}")

    hist = Counter(scores)
    print(f"\n=== score histogram ===")
    for s in sorted(hist, reverse=True):
        print(f"  {s}: {hist[s]}")

    # Per-partial: collect scores per partial; basin ceiling = max
    by_partial = defaultdict(list)
    for r in rows:
        by_partial[r["partial"]].append(r["matched"])
    print(f"\n=== per-partial summary (top by max) ===")
    items = sorted(by_partial.items(), key=lambda kv: -max(kv[1]))
    for partial, sc in items[:20]:
        name = Path(partial).stem
        print(f"  {name:30s} max={max(sc):>3} mean={sum(sc)/len(sc):>5.1f} N={len(sc)}")

    print(f"\n=== TOP-10 boards ===")
    top = sorted(rows, key=lambda r: -r["matched"])[:10]
    for r in top:
        print(f"  {Path(r['partial']).stem:30s} seed={r['seed']} → {r['matched']}")

    if max(scores) >= 459:
        print(f"\n🎯 NEW RECORD candidate: max={max(scores)} (≥459) — RESCORE VERIFY!")
    elif max(scores) >= 458:
        print(f"\n✨ Tied vol-32 458 record: max={max(scores)} — RESCORE VERIFY!")
    elif max(scores) >= 457:
        print(f"\n   Tied 457 record: max={max(scores)}")
    else:
        print(f"\n   Max={max(scores)} (below 457)")

    print(f"\n=== verification reminder ===")
    print(f"ALWAYS rescore the top boards with `target/release/rescore_board`")
    print(f"to verify against the piece_swap_hillclimb bug (vol-34).")


if __name__ == "__main__":
    main()
