#!/usr/bin/env python3
"""V129 — Summarize all PALIMPSEST attacks (and FPL probe).

Auto-collects results from output/vol-125/fpl_cross_basin_* and
output/vol-129/*/ directories. Prints a single table.
"""

from __future__ import annotations
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def parse_alns_log(path):
    """Extract final matched count from an ALNS log."""
    if not path.exists(): return None
    try:
        content = open(path).read()
    except: return None
    matches = re.findall(r"matched=(\d+)", content)
    if not matches: return None
    return max(int(m) for m in matches)


def main():
    print("V129 attack results summary")
    print("=" * 80)
    print()

    # FPL cross-basin probe
    print("V125-T34 FPL cross-basin probe (61 McGavin pair-tuples pinned):")
    fpl_dir = REPO / "output/vol-125"
    for d in sorted(fpl_dir.glob("fpl_cross_basin_*")):
        for log in sorted(d.glob("alns_seed*.log")):
            seed = re.search(r"seed(\d+)", log.name).group(1)
            score = parse_alns_log(log)
            print(f"  {d.name}  seed={seed}: best={score}")
    print()

    # PALIMPSEST escape pinning v1 (full overlay - 251 pins)
    print("V129-T6 escape-pinning v1 (full 251-position overlay):")
    for d in sorted((REPO / "output/vol-129").glob("escape_pinning_*")):
        for log in sorted(d.glob("alns_seed*.log")):
            seed = re.search(r"seed(\d+)", log.name).group(1)
            score = parse_alns_log(log)
            print(f"  {d.name}  seed={seed}: best={score}")
    print()

    # PALIMPSEST escape pinning v2 (K=16/32/64)
    print("V129-T7 escape-pinning v2 (K-sweep, top trap positions):")
    for d in sorted((REPO / "output/vol-129").glob("escape_v2_*")):
        for log in sorted(d.glob("alns_*.log")):
            m = re.search(r"alns_K(\d+)_s(\d+)", log.name)
            if m:
                K, seed = m.group(1), m.group(2)
                score = parse_alns_log(log)
                print(f"  {d.name}  K={K} seed={seed}: best={score}")
    print()

    # (1,0,3,2) basin attack
    print("V129-T10 (1,0,3,2) basin attack:")
    log = Path("/tmp/alns_1032_460_s42.log")
    score = parse_alns_log(log)
    print(f"  /tmp/alns_1032_460_s42.log: best={score}")
    print()


if __name__ == "__main__":
    main()
